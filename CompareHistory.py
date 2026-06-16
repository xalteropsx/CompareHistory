from collections import deque
import difflib
from functools import partial
from itertools import chain, tee
import os
import re
import threading
import sublime
import sublime_plugin
import pickle
from pathlib import Path
from datetime import datetime
import gzip

def sbs_settings():
    class Settings:
        def __init__(self):
            self.defaults = {
                "read_only": False,
                "outlines_only": False,
                "ignore_whitespace": False,
                "ignore_case": False,
                "ignore_pattern": "",
                "hide_sidebar": False,
                "hide_menu": False,
                "hide_minimap": False,
                "hide_status_bar": False,
                "hide_tabs": False,
                "display_prefix": "",
                "line_count_popup": False,

            }
        
        def get(self, key, default=None):
            return self.defaults.get(key, default)
        
        def has(self, key):
            return key in self.defaults
    
    return Settings()




def triplewise(iterable):
    t1, t2, t3 = tee(iterable, 3)
    next(t3, None)
    next(t3, None)
    next(t2, None)
    return zip(t1, t2, t3)


class sbs_replace_view_contents(sublime_plugin.TextCommand):
    def run(self, edit, text):
        view = self.view
        readonly = view.is_read_only()
        if readonly:
            view.set_read_only(False)
        view.replace(edit, sublime.Region(0, view.size()), text)
        if readonly:
            view.set_read_only(True)


class SbsLayoutPreserver(sublime_plugin.EventListener):
    def on_pre_close(self, view):
        if view.settings().get('is_sbs_compare'):
            sublime.set_timeout(lambda: view.window().run_command('close_window'), 10)


sbs_markedSelection = ''


class sbs_mark_sel(sublime_plugin.TextCommand):
    def run(self, edit):
        global sbs_markedSelection
        sel = self.view.sel()[0]
        sbs_markedSelection = self.view.substr(sel)

# class sbs_compare_files(sublime_plugin.ApplicationCommand):
#     def run(self, A=None, B=None):
#         global sbs_files
#         if A and B and os.path.isfile(A) and os.path.isfile(B):
#             sbs_files = [os.path.abspath(A), os.path.abspath(B)]
#             sublime.active_window().run_command('sbs_compare')


last_file = [None,None]

def get_view_contents(view):
        return view.substr(sublime.Region(0, view.size()))

class sbs_compare(sublime_plugin.TextCommand):
    def is_enabled(self, compare_selections=False , last_selections=False):
        if compare_selections:
            return len(self.view.sel()) == 2 or any(sbs_markedSelection)
        if last_selections:
            return  last_file[0] is not None
        return True

    # @staticmethod
   

    def run(self, edit, with_active=False, group=-1, index=-1, compare_selections=False, last_selections=False):
        global sbs_markedSelection, sbs_files,last_file
        
        view = self.view
        window = view.window()
        
        # if sbs_files:
        #     v1, v2 = window.open_file(sbs_files[0]), window.open_file(sbs_files[1])
        #     self.compare_after_load(v1, v2, sbs_files[0], sbs_files[1])
        #     sbs_files.clear()
        if compare_selections:
            sel = view.sel()
            if len(sel) == 2:
                textA, textB = view.substr(sel[0]), view.substr(sel[1])
            else:
                textA, textB = self.view.substr(sel[0]), sbs_markedSelection or view.substr(sel[0])
                # sbs_markedSelection = ''
            self.create_comparison(textA, textB, view.settings().get('syntax'), 'selection A', 'selection B')
        else:
            tabs = [(v.file_name() or v.name() or 'untitled', v) for v in window.views() if v.id() != view.id()]
            if len(tabs) == 1:
                # FIXED: Pass the actual tab name instead of False
                self.create_comparison(
                    get_view_contents(view), 
                    get_view_contents(tabs[0][1]), 
                    view.settings().get('syntax'), 
                    view.file_name() or view.name() or 'untitled',  # Use actual filename
                    tabs[0][0]  # Other tab name
                )
            elif with_active:
                active_group = window.get_view_index(view)[0]
                other = window.active_view_in_group(0 if active_group else 1)
                self.create_comparison(
                    get_view_contents(view), 
                    get_view_contents(other),
                    view.settings().get('syntax'), 
                    view.file_name() or view.name() or 'untitled',  # Use actual filename
                    other.file_name() or other.name()
                )
            else:
                if last_selections:
                    self.create_comparison(
                        get_view_contents(view), 
                        None,
                        view.settings().get('syntax'), 
                        view.file_name() or view.name() or 'untitled',
                        'Target',last_selections
                    )
                else:
                    items = [[os.path.basename(t[0]), t[0]] for t in tabs]
                    window.show_quick_panel(
                        items, 
                        lambda i: self.create_comparison(
                            get_view_contents(view), 
                            get_view_contents(tabs[i][1]),
                            view.settings().get('syntax'), 
                            view.file_name() or view.name() or 'untitled',  # Use actual filename
                            tabs[i][0]
                        )
                    )

    def compare_after_load(self, v1, v2, f1, f2):
        if v1.is_loading() or v2.is_loading():
            sublime.set_timeout(lambda: self.compare_after_load(v1, v2, f1, f2), 10)
        else:
            c1, c2 = get_view_contents(v1), get_view_contents(v2)
            v1.close()
            v2.close()
            self.create_comparison(c1, c2, v1.settings().get('syntax'), f1, f2)

    def create_comparison(self, text1, text2, syntax, name1, name2, last_selections=False):
        global last_file
        if last_selections:
             text2,name2 = last_file
        else:
            last_file = [text2,name2]
        win = sublime.active_window()
        win.run_command('new_window')
        new_win = sublime.active_window()
        new_win.set_layout({"cols": [0.0, 0.5, 1.0], "rows": [0.0, 1.0], "cells": [[0,0,1,1], [1,0,2,1]]})
        
        settings = sbs_settings()
        for attr in ['sidebar', 'menu', 'minimap', 'status_bar', 'tabs']:
            if settings.get(f'hide_{attr}', False):
                getattr(new_win, f'set_{attr}_visible')(False)
        
        # Ensure names are strings
        if name1 is False or name1 is None:
            name1 = 'untitled'
        if name2 is False or name2 is None:
            name2 = 'untitled'
        
        v1 = new_win.new_file(syntax=syntax)
        v2 = new_win.new_file(syntax=syntax)
        
        prefix = settings.get('display_prefix', '')
        v1.set_name(f"{prefix}{os.path.basename(str(name1))} (Current)")
        v2.set_name(f"{prefix}{os.path.basename(str(name2))} (Target)")
        
        for v in (v1, v2):
            v.set_scratch(True)
            v.settings().set("is_sbs_compare", True)
            v.settings().set('word_wrap', False)
            if settings.get('read_only', False):
                v.set_read_only(True)
        
        new_win.set_view_index(v1, 0, 0)
        new_win.set_view_index(v2, 1, 0)
        
        self.compare_views(v1, v2, text1, text2)
        ViewScrollSyncer(new_win, [v1, v2])
        new_win.focus_view(v1)

    @classmethod
    def compare_views(cls, v1, v2, t1, t2):
        textA, textB, highlightsA, highlightsB, intraline = compute_diff(t1, t2)
        
        v1.run_command('sbs_replace_view_contents', {'text': textA})
        v2.run_command('sbs_replace_view_contents', {'text': textB})
        
        for v in (v1, v2):
            v.sel().clear()
            v.sel().add(sublime.Region(0))
            v.show(0)
        
        highlight_lines(v1, highlightsA, 'A')
        highlight_lines(v2, highlightsB, 'B')
        

def compute_diff(text1, text2):
    linesA = deque(text1.splitlines(False))
    linesB = deque(text2.splitlines(False))
    
    diff_text1, diff_text2 = text1, text2
    if sbs_settings().has('ignore_pattern'):
        p = re.compile(sbs_settings().get('ignore_pattern'), re.MULTILINE)
        diff_text1 = p.sub('', diff_text1)
        diff_text2 = p.sub('', diff_text2)
    if sbs_settings().get('ignore_whitespace', False):
        diff_text1 = re.sub(r'[ \t]', '', diff_text1)
        diff_text2 = re.sub(r'[ \t]', '', diff_text2)
    if sbs_settings().get('ignore_case', False):
        diff_text1, diff_text2 = diff_text1.lower(), diff_text2.lower()
    
    diff = difflib.ndiff(diff_text1.splitlines(False), diff_text2.splitlines(False), charjunk=None)
    bufferA, bufferB = [], []
    hlA, hlB = [], []
    intraline = []
    open_block = False
    
    for prev_line, line, next_line in triplewise(chain([""], diff, [""])):
        code = line[:1]
        
        if code == " ":
            bufferA.append(linesA.popleft())
            bufferB.append(linesB.popleft())
            open_block = False
            
        elif code == "-":
            bufferA.append(linesA.popleft())
            hlA.append(len(bufferA)-1)
            if not next_line.startswith("+"):
                bufferB.append("")
            open_block = True
            
        elif code == "+":
            bufferB.append(linesB.popleft())
            hlB.append(len(bufferB)-1)
            if open_block:
                intraline.append((len(bufferB)-1, bufferA[-1], bufferB[-1]))
            else:
                bufferA.append("")
            open_block = False
            
        elif code == "?":
            continue
    
    return "\n".join(bufferA), "\n".join(bufferB), hlA, hlB, intraline



def highlight_lines(view, lines, col):
    # regions = [sublime.Region(view.text_point(n, 0), view.text_point(n + 1, -1)) for n in lines]
    # markers = [view.text_point(n, 0) for n in lines]

    regions = []
    markers = []
    
    for n in lines:
        line_start = view.text_point(n, 0)
        markers.append(line_start)
        
        # Get the line region using view.line()
        line_region = view.line(line_start)
        regions.append(line_region)
    # Use DRAW_OUTLINED for outline only
    draw_flags = sublime.DRAW_OUTLINED
    # print(regions,markers)
    # if len(regions[0]):
    if col == 'A':
        # Red outline for deleted lines
        view.add_regions(
            f'diff_highlighted-{col}', 
            regions, 
            'constant.character.escape',  # Typically cyan/teal
            '',
            draw_flags
        )
    else:
        # Cyan outline for inserted lines
        view.add_regions(
            f'diff_highlighted-{col}', 
            regions, 
            'invalid.illegal',  # Typically red color
            '',
            draw_flags
        )
    
    view.settings().set('sbs_markers', markers)




class ViewScrollSyncer:
    def __init__(self, window, views):
        self.window, self.views = window, views
        self.run()
    
    def run(self):
        if not self.window.is_valid() or self.window.id() != sublime.active_window().id():
            sublime.set_timeout(self.run, 50)
            return
        
        v1, v2 = self.views
        if not (v1.is_valid() and v2.is_valid()):
            return
        
        p1, p2 = v1.viewport_position(), v2.viewport_position()
        if p1 != p2:
            last1 = (v1.settings().get('viewsync_last0', 0), v1.settings().get('viewsync_last1', 0))
            last2 = (v2.settings().get('viewsync_last0', 0), v2.settings().get('viewsync_last1', 0))
            
            if last1 != p1:
                for v in (v1, v2):
                    v.settings().set('viewsync_last0', p1[0])
                    v.settings().set('viewsync_last1', p1[1])
                v2.set_viewport_position(p1, False)
            elif last2 != p2:
                for v in (v1, v2):
                    v.settings().set('viewsync_last0', p2[0])
                    v.settings().set('viewsync_last1', p2[1])
                v1.set_viewport_position(p2, False)
        
        sublime.set_timeout(self.run, 10)


class sbs_prev_diff(sublime_plugin.TextCommand):
    def is_visible(self):
        return self.view.settings().get("is_sbs_compare", False)
    
    def run(self, edit, string=''):
        pos = self.view.sel()[0].begin()
        markers = self.view.settings().get('sbs_markers', [])
        found = None
        for m in reversed(markers):
            if m < pos:
                found = m
                break
        if found is not None:
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(found))
            self.view.show(found)


class sbs_next_diff(sublime_plugin.TextCommand):
    def is_visible(self):
        return self.view.settings().get("is_sbs_compare", False)
    
    def run(self, edit, string=''):
        pos = self.view.sel()[0].begin()
        markers = self.view.settings().get('sbs_markers', [])
        for m in markers:
            if m > pos:
                self.view.sel().clear()
                self.view.sel().add(sublime.Region(m))
                self.view.show(m)
                return



def rootx(self,projectroot,filepath):
    store = str(filepath).split(projectroot)
    store = store[1] if len(store) == 2 else '/tmp/' + re.sub(r'[\\/:*?"<>|]', '_', str(filepath))
    opath = self.history  / (projectroot  + store)  #base_path
    return Path(re.sub(r'\.[^.]+$', '.gz', str(opath)))

class VersionedList:
    def __init__(self, root='History', base=os.path.expanduser("~/.cache"), limit=10):
        self.limit = limit
        self.history = Path(base) / 'subl' #/ root
        self.watched_files = {}

    def readfile(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def save_version(self, filepath, projectroot):
        filepath = Path(filepath)
        opath = rootx(self,projectroot,filepath)
        # opath = Path(opath)
        opath.parent.mkdir(parents=True, exist_ok=True)
        data = self.read(opath)
        content = self.readfile(filepath)
        # print(opath,'opath')
        if data and data[0] == content:
            return
        
        data.insert(0, content)
        data = data[:self.limit]
        
        with gzip.open(opath, 'wb') as f:
            pickle.dump(data, f)

    def read(self, path):
        if not path.exists():
            return []
        try:
            with gzip.open(path, 'rb') as f:
                return pickle.load(f)
        except (pickle.PickleError, EOFError, gzip.BadGzipFile):
            return []

    def get_versions(self, filepath, projectroot):
        filepath = Path(filepath)
        opath = rootx(self,projectroot,filepath)
        return self.read(opath)

    def watch_file(self, filepath):
        filepath = str(filepath)
        if filepath not in self.watched_files:
            self.watched_files[filepath] = None

    def on_file_changed(self, filepath):
        if filepath in self.watched_files:
            self.save_version(filepath)


class FileWatcher(sublime_plugin.EventListener):
    def __init__(self):
        self.vf = None
        self.save_timer = None

    def init_vf(self):
        if self.vf is None:
            settings = sublime.load_settings('Preferences.sublime-settings')
            base = settings.get('versioned_history_base', os.path.expanduser("~/.cache"))
            limit = settings.get('versioned_history_limit', 10)
            self.vf = VersionedList(base=base, limit=limit)

    def on_post_save(self, view):
        if view.is_scratch() or not view.file_name():
            return
        
        self.init_vf()
        filepath = view.file_name()
        project_root = self._get_project_root(view)
        
        if self.save_timer:
            self.save_timer.cancel()
        
        from threading import Timer
        self.save_timer = Timer(0.5, self._save_version, [filepath, project_root])
        self.save_timer.start()
    
    def _save_version(self, filepath, project_root):
        sublime.set_timeout(lambda: self._do_save(filepath, project_root), 10)
    
    def _do_save(self, filepath, project_root):
        self.vf.save_version(filepath, project_root)
        print(f"Version saved for: {filepath} (Project: {project_root or 'None'})")


    def _get_project_root(self, view):
        window = view.window()
        if not window:
            return None
        
        folders = window.folders()
        if folders:
            return Path(folders[0]).name
        
        filepath = view.file_name()
        if filepath:
            return Path(filepath).parent.name
        
        return None




class VersionedHxSettings(sublime_plugin.ApplicationCommand):
    def run(self):
        settings = sublime.load_settings('Preferences.sublime-settings')
        current_base = settings.get('versioned_history_base', os.path.expanduser("~/.cache"))
        current_limit = settings.get('versioned_history_limit', 10)
        
        items = [
            [f"Set History Base Directory", f"Current: {current_base}"],
            [f"Set Version Limit", f"Current: {current_limit}"],
        ]
        
        window = sublime.active_window()
        window.show_quick_panel(items, self.on_select)
    
    def on_select(self, index):
        if index == 0:
            sublime.active_window().run_command("set_versioned_history_base")
        elif index == 1:
            sublime.active_window().run_command("set_versioned_history_limit")


# class SetVersionedHistoryBase(sublime_plugin.WindowCommand):
#     def run(self):
#         def on_done(text):
#             if text:
#                 settings = sublime.load_settings('Preferences.sublime-settings')
#                 settings.set('versioned_history_base', text)
#                 sublime.save_settings('Preferences.sublime-settings')
#                 sublime.message_dialog(f"History base set to: {text}")
        
#         self.window.show_input_panel("History Base Directory:", 
#                                      os.path.expanduser("~/.cache"), on_done, None, None)
class SetVersionedHistoryBase(sublime_plugin.WindowCommand):
    def run(self):
        settings = sublime.load_settings('Preferences.sublime-settings')
        current_base = settings.get('versioned_history_base', os.path.expanduser("~/.cache"))
        print(settings.get('versioned_history_base'),'settings======')
        def on_done(text):
            if text:
                settings.set('versioned_history_base', text)
                sublime.save_settings('Preferences.sublime-settings')
                sublime.message_dialog(f"History base set to: {text}")
        
        self.window.show_input_panel(
            "History Base Directory:", 
            current_base, 
            on_done, 
            None, 
            None
        )


class SetVersionedHistoryLimit(sublime_plugin.WindowCommand):
    def run(self):
        settings = sublime.load_settings('Preferences.sublime-settings')
        current_limit = str(settings.get('versioned_history_limit', 10))
        
        def on_done(text):
            try:
                limit = int(text)
                if limit > 0:
                    settings = sublime.load_settings('Preferences.sublime-settings')
                    settings.set('versioned_history_limit', limit)
                    sublime.save_settings('Preferences.sublime-settings')
                    sublime.message_dialog(f"Version limit set to: {limit}")
                else:
                    sublime.message_dialog("Limit must be positive")
            except ValueError:
                sublime.message_dialog("Please enter a valid number")
        
        self.window.show_input_panel(
            "Version Limit (max versions to keep):", 
            current_limit, 
            on_done, 
            None, 
            None
        )

class ClearFileHistory(sublime_plugin.TextCommand):
    def is_visible(self):
        return bool(self.view.file_name())
    
    def run(self, edit):
        filepath = self.view.file_name()
        fw = FileWatcher()
        fw.init_vf()
        projectroot = fw._get_project_root(self.view)

        # opath = fw.vf.history  / (projectroot  + (filepath.split(projectroot))[1])  #base_path
        opath = rootx(fw.vf,projectroot,filepath)
        # history_file = fw.vf.history / base_path
        
        if opath.exists():
            opath.unlink()
            sublime.message_dialog(f"History cleared for {os.path.basename(filepath)}")
        else:
            sublime.message_dialog("No history found for this file")



class ShowVersionHistoryCommand(sublime_plugin.TextCommand):
    def is_visible(self):
        return bool(self.view.file_name())

    def run(self, edit):
        filepath = self.view.file_name()
        
        fw = FileWatcher()
        fw.init_vf()
        parent = fw._get_project_root(self.view)
        versions = fw.vf.get_versions(filepath, parent)
        
        if not versions:
            sublime.message_dialog("No version history found for this file")
            return
        versions = versions[1:]
        
        # Store versions for later use
        self.versions = versions
        self.current_file = filepath
        self.syntax = self.view.settings().get('syntax')
        
        items = []
        for i, version in enumerate(versions):
            timestamp = f"Version {len(versions)-i}"
            preview = version[:50].replace('\n', ' ')
            items.append([timestamp, preview])
        
        # Add comparison options
        items.append(["─" * 40, ""])
        items.append(["Compare All Versions", "Open side-by-side comparison"])
        # items.append(["Compare with Current", "Compare version with current file"])
        
        def on_select(index):
            if index < 0:
                return
            if index == len(versions):
                return  # Separator
            if index == len(versions) + 1:
                self.compare_all_versions()
            # elif index == len(versions) + 2:
            #     self.compare_with_current()
            else:
                # selected_version = versions[index]
                # self.show_version(selected_version, index)
                # self.compare_with_current()
                current_content = get_view_contents(self.view)
                self.create_comparison_view(current_content, self.versions[index], "Current File", f"Version {len(self.versions)-index}")

        
        self.view.window().show_quick_panel(items, on_select)
    
    def show_version(self, content, version_index=None):
        window = self.view.window()
        new_view = window.new_file()
        new_view.run_command('sbs_replace_view_contents', {'text': content})
        new_view.set_name(f"Version {len(self.versions)-version_index if version_index is not None else 'History'}")
        new_view.set_scratch(True)
        new_view.assign_syntax(self.syntax)
    
    def compare_with_current(self):
        """Compare selected version with current file."""
        window = self.view.window()
        current_content = get_view_contents(self.view)
        
        items = []
        for i, version in enumerate(self.versions):
            timestamp = f"Version {len(self.versions)-i}"
            preview = version[:50].replace('\n', ' ')
            items.append([timestamp, preview])
        
        def on_select(index):
            if index >= 0:
                self.create_comparison_view(current_content, self.versions[index], 
                                           "Current File", f"Version {len(self.versions)-index}")
        
        window.show_quick_panel(items, on_select)

    def compare_all_versions(self):
        window = self.view.window()
        if not window:
            return

        # Create new window
        window.run_command('new_window')
        new_win = sublime.active_window()

        # Remove default untitled view
        for v in new_win.views():
            if v.is_scratch() and not v.file_name() and v.name() == "":
                v.close()
                break

        num_versions = len(self.versions)
        if num_versions == 0:
            sublime.message_dialog("No versions found")
            return

        
        current_content = get_view_contents(self.view)
        current_syntax = self.view.settings().get('syntax')

        
        total_panes = 1 + num_versions
        
        max_panes = 6
        visible_panes = min(total_panes, max_panes)

        
        if visible_panes <= 3:
            cols = visible_panes
            rows = 1
        elif visible_panes <= 4:
            cols = 2
            rows = 2
        else:  
            cols = 3
            rows = 2

        
        col_pos = [i / cols for i in range(cols + 1)]
        row_pos = [i / rows for i in range(rows + 1)]
        cells = [[c, r, c + 1, r + 1] for r in range(rows) for c in range(cols)]
        new_win.set_layout({"cols": col_pos, "rows": row_pos, "cells": cells})

        
        master = new_win.new_file()
        master.run_command('sbs_replace_view_contents', {'text': current_content})
        master.set_name("Current")
        master.set_scratch(True)
        master.assign_syntax(current_syntax)
        new_win.set_view_index(master, 0, 0)

        
        version_views = []
        lastv = []
        
        for idx, version in enumerate(self.versions):
            
            cell_idx = idx + 1
            if cell_idx >= visible_panes:
                
                target_group = visible_panes - 1
                tab_index = cell_idx - visible_panes + 1
            else:
                target_group = cell_idx
                tab_index = 0

            v = new_win.new_file()
            v.run_command('sbs_replace_view_contents', {'text': version})
            v.set_name(f"v{num_versions - idx}")
            v.set_scratch(True)
            v.assign_syntax(current_syntax)
            new_win.set_view_index(v, target_group, tab_index)
            version_views.append(v)

            if idx == 0:
                # sbs_compare.compare_views(master, v, current_content, version)
                threading.Thread(target=lambda: sbs_compare.compare_views(master, v, current_content, version)).start()
            else:
                # sbs_compare.compare_views(lastv[0], v, lastv[1], version)
                threading.Thread(target=lambda: sbs_compare.compare_views(lastv[0], v, lastv[1], version)).start()
                # self.hypercolor(v,current_content,version)

            lastv = [v,version]
            
        
        if version_views:
            ViewScrollSyncer(new_win, [master, version_views[0]])


    @staticmethod
    def hypercolor(v1, t1, t2):
        textA, textB, highlightsA, highlightsB, intraline = compute_diff(t1, t2)
        
        v1.run_command('sbs_replace_view_contents', {'text': textA})
        # v2.run_command('sbs_replace_view_contents', {'text': textB})
        
        # for v in (v1, v2):
        v1.sel().clear()
        v1.sel().add(sublime.Region(0))
        v1.show(0)
        
        highlight_lines(v1, highlightsA, 'A')


  
    def create_comparison_view(self, text1, text2, name1, name2):
        window = self.view.window()
        window.run_command('new_window')
        new_win = sublime.active_window()
        new_win.set_layout({
            "cols": [0.0, 0.5, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
        })
        
        v1 = new_win.new_file()
        v2 = new_win.new_file()
        v1.set_name(name1)
        v2.set_name(name2)
        v1.assign_syntax(self.syntax)
        v2.assign_syntax(self.syntax)
        
        v1.run_command('sbs_replace_view_contents', {'text': text1})
        v2.run_command('sbs_replace_view_contents', {'text': text2})
        
        for v in (v1, v2):
            v.set_scratch(True)
            v.settings().set('word_wrap', False)
        
        new_win.set_view_index(v1, 0, 0)
        new_win.set_view_index(v2, 1, 0)
        
        # Compare the two versions
        sbs_compare.compare_views(v1, v2, text1, text2)
        ViewScrollSyncer(new_win, [v1, v2])

