import sublime
import os
import platform
import subprocess
import threading
import socket
import traceback
import fnmatch

DEBUG = True
DEBUG = False
PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
RUN_PATH = os.path.join(PACKAGE_PATH, 'backend_run.js')
if DEBUG:
    RUN_PATH = os.path.join(PACKAGE_PATH, 'backend', 'run.js')

def debug(s, data=None, force=False):
    if (DEBUG or force):
        message = str(s)
        if (data is not None):
            message = message + ': ' + str(data)
        print(message)

def run_command(command, data=None, callback=None):
    debug('Run command', [command, data])
    json = sublime.encode_value(data)
    err = None
    out = None
    try:
        (err, out) = exec(['node', RUN_PATH, command, json])
    except Exception as e:
        err = traceback.format_exc()
    if bool(err):
        if callback is not None:
            return callback(err, None)
        raise err
    debug('Trying to decode', out)
    result = sublime.decode_value(out)
    if callback is not None:
        return callback(None, result)
    return result

def run_command_async(command, data=None, callback=None):
    thread = threading.Thread(target=run_command, args=(command, data, callback))
    thread.start()

def exec(cmd):
    if os.name == 'nt':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.Popen(cmd, cwd=PACKAGE_PATH, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, startupinfo=si)
    else:
        proc = subprocess.Popen(cmd, cwd=PACKAGE_PATH, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    outs, errs = proc.communicate()
    err = errs.decode().strip()
    if bool(err):
        debug('Exec error', err, True)
    return (err, outs.decode().strip())

def exec_async(cmd, done=None):
    def run_thread(cmd, done):
        (err, result) = exec(cmd)
        if (done is not None):
            done(err, result)
        return
    thread = threading.Thread(target=run_thread, args=(cmd, done))
    thread.start()
    return thread

def unixify(path):
    path = path.replace('\\', '/')
    ext3 = path[-3:]
    if (ext3 == '.ts' or ext3 == '.js'):
        return path[0:-3]
    ext4 = path[-4:]
    if (ext4 == '.tsx' or ext4 == '.jsx'):
        return path[0:-4]
    return path

def get_panel_item(root, item):
    # Prepare string to show in window's quick panel.
    module = item.get('module')
    name = item.get('name')
    # TODO: Handle case when name is none (browserify)
    if name is None:
        return None
    if (module is not None):
        return module + '/' + name
    filepath = os.path.normpath(item['filepath'])[len(root) + 1:]
    return unixify(filepath) + '/' + name

def norm_path(base, to):
    return os.path.normpath(os.path.join(os.path.dirname(base), to))

def on_done_func(choices, func):
    # Return a function which is used with sublime list picking.
    def on_done(index):
        if index >= 0:
            return func(choices[index])
    return on_done

def is_excluded_file(filepath, exclude_patterns):
    if exclude_patterns is None or len(exclude_patterns) == 0:
        return False
    for pattern in exclude_patterns:
        if filepath.startswith(pattern): return True
        if fnmatch.fnmatch(filepath, pattern): return True
    return False

def get_setting(name, default):
    result = None
    project_data = sublime.active_window().project_data()
    if project_data is not None:
        result = project_data.get(name)
    if result is None:
        settings = sublime.load_settings('import_helper.sublime-settings') or {}
        result = settings.get(name)
    if result is None:
        preferences = sublime.load_settings('Preferences.sublime-settings')
        result = preferences.get(name)
    if result is None:
        result = default
    return result

def get_import_root():
    window = sublime.active_window()
    project_file = window.project_file_name()
    if project_file is None:
        return None
    project_data = window.project_data() or {}
    result = project_data.get('import_root')
    if result is None:
        result = project_data['folders'][0]['path']
    return norm_path(project_file, result)