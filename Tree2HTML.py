import os, sys, html, pathlib, webbrowser, traceback, json, string, stat
from datetime import datetime
from tkinter import Tk, filedialog, Button, Label, Entry, Checkbutton, IntVar, StringVar, LEFT, RIGHT, X, Frame
from pathlib import Path
import threading
import queue

dirs_count = 0
files_count = 0
current_process_path = ""
progress_queue = queue.Queue()
is_progress_running = False
IGNORE_NAMES = set()
is_stop_requested = False

def get_app_dir():
    """获取程序实际运行目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))

DEFAULT_OUTPUT = "snapshot.html"
JSON_FILE_PATH = os.path.join(get_app_dir(), "IGNORE_NAMES.json")
TEMPLATE_FILE_PATH = os.path.join(get_app_dir(), "template.html")

# 忽略规则默认列表
DEFAULT_IGNORE_LIST = [
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".AppleDouble",
    ".DocumentRevisions-V100",
    ".Spotlight-V100",
    ".TemporaryItems",
    ".Trashes",
    ".fseventsd",
    "System Volume Information",
    "$RECYCLE.BIN"
]

def center_window(root):
    """让主窗口在屏幕正中央显示，适配所有分辨率"""
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = root.winfo_width()
    window_height = root.winfo_height()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"+{x}+{y}")

def check_template_exists():
    """检查模板文件是否存在，不存在则提示并退出"""
    if not os.path.exists(TEMPLATE_FILE_PATH):
        print(f"错误：模板文件 {TEMPLATE_FILE_PATH} 不存在，请确保该文件与程序同目录！")
        sys.exit(1)

def load_ignore_names():
    """读取忽略规则JSON文件，无文件则自动创建"""
    try:
        if not os.path.exists(JSON_FILE_PATH):
            with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_IGNORE_LIST, f, ensure_ascii=False, indent=2)
            print(f"已自动生成忽略规则文件: {JSON_FILE_PATH}")
        
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            ignore_list = json.load(f)
        # 统一转为小写，不区分大小写匹配
        ignore_list_lower = [item.lower() for item in ignore_list]
        return set(ignore_list_lower)
    except Exception as e:
        print(f"读取忽略规则文件失败，使用默认规则: {e}")
        # 默认规则也转小写
        return set([item.lower() for item in DEFAULT_IGNORE_LIST])

def is_file_hidden(path: str) -> bool:
    """隐藏属性判断"""
    if not os.path.exists(path):
        return False
    try:
        file_stat = os.stat(path)
        filename = os.path.basename(path)
        if sys.platform == 'win32':
            # Windows系统
            return (file_stat.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN) != 0
        elif sys.platform == 'darwin':
            # macOS系统
            is_hidden_by_flag = (file_stat.st_flags & stat.UF_HIDDEN) != 0
            is_hidden_by_name = filename.startswith('.') and filename not in ('.', '..')
            return is_hidden_by_flag or is_hidden_by_name
        else:
            # Linux系统
            is_hidden_by_name = filename.startswith('.') and filename not in ('.', '..')
            return is_hidden_by_name
    except (OSError, PermissionError):
        # 权限不足/访问失败时，默认视为「非隐藏」，避免程序中断
        return False

def should_ignore(name: str, full_path: str, include_hidden_attr=False):
    """决定是否忽略该文件/文件夹"""
    # 判断名称转小写后匹配忽略规则
    if name.lower() in IGNORE_NAMES:
        return True
    if is_file_hidden(full_path) and not include_hidden_attr:
        return True
    return False

def human_size(num):
    for unit in ['B','KB','MB','GB','TB']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}PB"

def mtime_str(epoch):
    try:
        return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(epoch)

def build_tree_li(path, add_file_links=False, include_error_dirs=True, include_hidden_attr=False):
    global dirs_count, files_count, is_stop_requested

    if is_stop_requested:
        return ""
    
    root_basename = os.path.basename(path)
    name = path if not root_basename else root_basename
    
    if root_basename != "" and should_ignore(name, path, include_hidden_attr):
        return ""

    progress_queue.put({"type": "path", "data": path})

    safe_name = html.escape(name, quote=True)  # 文件名特殊字符转义，防止HTML错乱
    data_name = name.lower()
    is_dir = os.path.isdir(path)
    try:
        st = os.stat(path)
    except Exception:
        st = None
    meta = ""
    if st:
        if is_dir:
            meta = f" <span class='meta'>[{datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}]</span>"
        else:
            meta = f" <span class='meta'>[{human_size(st.st_size)} | {datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}]</span>"

    if is_dir:
        is_dir_error = False
        try:
            entries = sorted(
                [e for e in os.listdir(os.path.abspath(path)) if not should_ignore(e, os.path.join(path, e), include_hidden_attr)],
                key=lambda s: s.lower()
            )
        except PermissionError:
            is_dir_error = True
            print(f"权限不足，无法访问目录: {os.path.abspath(path)}")
            entries = []
        except Exception as e:
            is_dir_error = True
            print(f"遍历目录失败: {os.path.abspath(path)}，错误: {e}")
            entries = []

        if is_dir_error and not include_error_dirs:
            return ""
        
        # 仅当目录有效/需包含时，才执行计数
        dirs_count += 1
        progress_queue.put({"type": "count", "data": (dirs_count, files_count)})

        cur_dir_num = 0
        cur_file_num = 0
        for item in entries:

            if is_stop_requested:
                return ""
            item_full_path = os.path.join(path, item)
            if os.path.isdir(item_full_path):
                cur_dir_num +=1
            else:
                cur_file_num +=1

        dir_data_attrs = f" data-dir-count='{cur_dir_num}' data-file-count='{cur_file_num}'"
        if is_dir_error:
            dir_data_attrs += " data-error='true'"

        children_html = "\n".join(
            x for x in (build_tree_li(os.path.join(path, e), add_file_links, include_error_dirs, include_hidden_attr) for e in entries) if x
        )
        li = f"<li class='dir collapsed' data-name='{data_name}'{dir_data_attrs}><span class='icon folder'></span><span class='label'>{safe_name}</span>{meta}"
        if children_html:
            li += f"<ul>\n{children_html}\n</ul>"
        li += "</li>"
        return li
    else:
        files_count += 1
        progress_queue.put({"type": "count", "data": (dirs_count, files_count)})
        if add_file_links:
            file_uri = Path(path).resolve().as_uri()
            label_html = f"<a href='{file_uri}' target='_blank'>{safe_name}</a>"
        else:
            label_html = safe_name  # 不勾选=纯文本，无任何链接
        return f"<li class='file' data-name='{data_name}'><span class='icon file'></span><span class='label'>{label_html}</span>{meta}</li>"

def generate_html(root_path, title=None, add_file_links=False, include_error_dirs=True, include_hidden_attr=False):
    global dirs_count, files_count
    dirs_count = 0
    files_count = 0
    title = title or f"{root_path.replace(os.sep, os.path.sep)}"
    root_basename = os.path.basename(root_path)
    root_display = html.escape(root_path if not root_basename else root_basename)
    
    tree_html = build_tree_li(root_path, add_file_links, include_error_dirs, include_hidden_attr)
    if not tree_html and os.path.isdir(root_path):
        tree_html = f"<li class='dir expanded' data-name='{root_path}' data-dir-count='0' data-file-count='0'><span class='icon folder'></span><span class='label'>{root_path}</span> <span class='meta'>[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]</span></li>"
    tree_html = tree_html.replace("class='dir collapsed'", "class='dir expanded'", 1)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(TEMPLATE_FILE_PATH, "r", encoding="utf-8") as f:
            html_template = f.read()
    except Exception as e:
        raise Exception(f"读取模板文件失败：{e}")

    template_vars = {
        "title": html.escape(title),
        "root_display": root_display,
        "dirs_count": dirs_count,
        "files_count": files_count,
        "now": now,
        "tree_html": tree_html
    }

    html_text = string.Template(html_template).safe_substitute(template_vars)
    return html_text

def generate_worker(folder, out, add_file_links, include_error_dirs, include_hidden_attr, generate_btn, status, do_generate):
    global is_stop_requested
    try:
        if is_stop_requested:
            progress_queue.put({"type": "error", "data": "用户已停止生成"})
            return
        
        html_text = generate_html(folder, add_file_links=add_file_links, include_error_dirs=include_error_dirs, include_hidden_attr=include_hidden_attr)
        
        # 生成后再次检测，避免写入无效文件
        if is_stop_requested:
            progress_queue.put({"type": "error", "data": "用户已停止生成，未保存文件"})
            return
        
        with open(out, "w", encoding="utf-8") as f:
            f.write(html_text)
        
        if open_var.get() and not is_stop_requested:
            webbrowser.open_new_tab(pathlib.Path(out).resolve().as_uri())
        
        progress_queue.put({"type": "finish", "data": out})
    except Exception as e:
        # 若非用户停止导致的错误，才提示
        if not is_stop_requested:
            progress_queue.put({"type": "error", "data": str(e)})
            print(traceback.format_exc())
        else:
            progress_queue.put({"type": "error", "data": "用户已停止生成"})
    finally:
        root.after(0, lambda btn=generate_btn, dg=do_generate: btn.config(text="生成快照", command=dg, state="normal"))

def choose_dir_and_generate():
    global include_hidden_attr_var, IGNORE_NAMES, root, is_progress_running, open_var
    global dirs_count, files_count, current_process_path, is_stop_requested
    
    root = Tk()
    root.title("Tree2HTML")
    root.geometry("650x185")
    center_window(root)

    dir_var = StringVar(value=os.getcwd())
    open_var = IntVar(value=1)
    link_var = IntVar(value=0)
    output_var = StringVar(value=os.path.join(os.getcwd(), DEFAULT_OUTPUT))
    include_hidden_attr_var = IntVar(value=0)
    include_error_dirs_var = IntVar(value=1)

    generate_btn = None
    status = None
    progress_label = None

    def update_progress():
        nonlocal progress_label, status, generate_btn
        global current_process_path, dirs_count, files_count, is_progress_running
        try:
            while not progress_queue.empty():
                msg = progress_queue.get_nowait()
                if msg["type"] == "path":
                    current_process_path = msg["data"]
                elif msg["type"] == "count":
                    dirs_count, files_count = msg["data"]
                elif msg["type"] == "finish":
                    status.config(text=f"文件已生成: {msg['data']}")
                    is_progress_running = False
                    return
                elif msg["type"] == "error":
                    status.config(text=f"{msg['data']}", fg="red")
                    is_progress_running = False
                    return
            progress_label.config(text=f"当前处理: {current_process_path} | 目录: {dirs_count} | 文件: {files_count}")
        except queue.Empty:
            pass
        if is_progress_running:
            root.after(100, update_progress)

    def browse():
        d = filedialog.askdirectory(initialdir=dir_var.get(), title="选择文件夹")
        if d: dir_var.set(d)

    def browse_output():
        default_path = output_var.get()
        f = filedialog.asksaveasfilename(
            initialdir=os.path.dirname(default_path),
            initialfile=DEFAULT_OUTPUT,
            title="选择快照文件保存位置",
            filetypes=(("HTML文件", "*.html"), ("所有文件", "*.*"))
        )
        if f: output_var.set(f)

    def do_generate():
        nonlocal generate_btn, status, progress_label
        global dirs_count, files_count, current_process_path, is_progress_running, IGNORE_NAMES, is_stop_requested
        folder = dir_var.get().strip()
        if not folder:
            status.config(text="错误：没有选择文件夹", fg="red")
            return
        out = output_var.get().strip()
        if not out:
            status.config(text="错误：没有选择输出文件路径", fg="red")
            return
        
        IGNORE_NAMES = load_ignore_names()
        
        # 重置所有进度变量，清空队列
        dirs_count = 0
        files_count = 0
        current_process_path = "初始化规则..."
        is_stop_requested = False
        while not progress_queue.empty():
            progress_queue.get()
        
        generate_btn.config(text="停止生成", command=stop_generate, state="normal")
        status.config(text="生成中，请稍后...", fg="green")
        
        threading.Thread(
            target=generate_worker,
            args=(folder, out, bool(link_var.get()), bool(include_error_dirs_var.get()), bool(include_hidden_attr_var.get()), generate_btn, status, do_generate),
            daemon=True
        ).start()
        
        is_progress_running = True
        root.after(100, update_progress)

    def stop_generate():
        """停止生成函数"""
        nonlocal generate_btn, status
        global is_stop_requested, is_progress_running
        is_stop_requested = True
        generate_btn.config(text="停止中...", state="disabled")
        status.config(text="正在停止生成，请稍候...", fg="orange")
        is_progress_running = False
        root.after(500, lambda btn=generate_btn, dg=do_generate: btn.config(text="生成快照", command=dg, state="normal"))

    top = Frame(root); top.pack(fill=X,padx=10,pady=8)
    Label(top, text="文件夹:").pack(side=LEFT)
    Entry(top, textvariable=dir_var).pack(side=LEFT, fill=X, expand=True, padx=6)
    Button(top, text="浏览", command=browse).pack(side=RIGHT)

    output_frame = Frame(root); output_frame.pack(fill=X,padx=10,pady=4)
    Label(output_frame, text="输出文件:").pack(side=LEFT)
    Entry(output_frame, textvariable=output_var).pack(side=LEFT, fill=X, expand=True, padx=6)
    Button(output_frame, text="浏览", command=browse_output).pack(side=RIGHT)

    mid = Frame(root); mid.pack(fill=X,padx=10,pady=6)
    Checkbutton(mid, text="生成后打开浏览器", variable=open_var).pack(side=LEFT)
    Checkbutton(mid, text="为文件添加本地链接", variable=link_var).pack(side=LEFT, padx=(15, 0))
    Checkbutton(mid, text="包含隐藏属性文件/文件夹", variable=include_hidden_attr_var).pack(side=LEFT, padx=(15, 0))
    Checkbutton(mid, text="包含问题目录", variable=include_error_dirs_var).pack(side=LEFT, padx=(15, 0))
    generate_btn = Button(mid, text="生成快照", command=do_generate)
    generate_btn.pack(side=RIGHT)

    progress_label = Label(root, text="准备就绪", anchor="w")
    progress_label.pack(fill=X, padx=10, pady=(2,4))

    status = Label(root, text="最后更新日期：2026.01.17 HAF半个水果 https://github.com/Little-Data/Tree2HTML", anchor="w", fg="green")
    status.pack(fill=X, padx=10, pady=(2,6))
    root.mainloop()

if __name__ == "__main__":
    check_template_exists()
    choose_dir_and_generate()
