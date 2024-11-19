import multiprocessing
import os
import ctypes
import subprocess
import shutil
import time
import json
from tqdm import tqdm
from multiprocessing import Process, Value
from concurrent.futures import ThreadPoolExecutor, as_completed

def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def read_json(file_path):
    if not os.path.isfile(file_path) :
        return None
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def copy_file(src, dst):
    try:
        shutil.copy(src, dst)
        return True, None
    except IOError as e:
        return False, e

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def is_directory_empty(directory):
    # 列出目录中的所有文件和子目录
    items = os.listdir(directory)
    # 判断目录是否为空
    return len(items) == 0

def rename_folder(src, new_name):
    # 获取文件夹的父目录
    parent_dir = os.path.dirname(src)
    # 构建新的文件夹路径
    new_path = os.path.join(parent_dir, new_name)
    # 重命名文件夹
    os.rename(src, new_path)
    print(f"文件夹已重命名：{src} -> {new_path}")

def rename_folder_with_shutil(src, new_name):
    # 获取文件夹的父目录
    parent_dir = os.path.dirname(src)
    # 构建新的文件夹路径
    new_path = os.path.join(parent_dir, new_name)
    # 重命名文件夹
    shutil.move(src, new_path)


def check_and_create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"文件夹 {directory} 已创建。")
    else:
        print(f"文件夹 {directory} 已经存在。")

def read_file(file_path,type = "rb"):
    try:
        if type == "rb":
            with open(file_path, type) as file:
                return file.read()
        elif type == "r":
            with open(file_path, type,encoding="utf-8") as file:
                return file.read()
    except IOError as e:
        print(f"无法读取文件 {file_path}: {e}")
        return None

def read_file_lines(file_path,type = "rb"):
    if type == "rb":
        with open(file_path, type) as file:
            return file.readlines()
    elif type == "r":
        with open(file_path, type, encoding="utf-8") as file:
            return file.readlines()
    return None

def write_file(file_path,content,type = "wb"):
    if type == "wb":
        with open(file_path, type) as file:
            file.write(content)
    elif type == "a" or type == "w":
        with open(file_path, type,encoding='utf-8') as file:
            file.write(content)

def run_command(command:list):
    try:
        # 执行命令并捕获输出
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"


def calculate_total_size(src):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(src):
        for f in filenames:
            with open(os.path.join(dirpath, f), 'rb') as src:
                fileinfo = os.fstat(src.fileno())
                total_size += fileinfo.st_size
    return total_size


def copy_file_chunk(src_file, dst_file, offset, chunk_size,copied_size_total,lock):
    with open(src_file, 'rb') as src, open(dst_file, 'r+b') as dst:
        src.seek(offset)
        dst.seek(offset)
        buffer = src.read(chunk_size)
        if buffer:
            bytes_written = dst.write(buffer)
            if bytes_written <0:
                print("catch")
            if bytes_written != len(buffer): raise IOError(
                f"写入失败：期望写入 {len(buffer)} 字节，但实际写入 {bytes_written} 字节")
            with lock:
                copied_size_total.value += bytes_written


def copy_file_with_progress(src_file, dst_file, copied_size, lock,chunk_size=1024 * 1024):  # 默认1MB
    file_size = os.path.getsize(src_file)
    with open(dst_file, 'wb') as dst:  # 创建目标文件
        dst.truncate(file_size)  # 预分配空间

    offsets = [(i, chunk_size) for i in range(0, file_size, chunk_size)]
    with ThreadPoolExecutor() as executor:
        futures = []
        for offset, size in offsets:
            futures.append(executor.submit(copy_file_chunk, src_file, dst_file, offset, size, copied_size, lock))
        for future in as_completed(futures):
            future.result()  # 确保每个块复制完成


def copy_folder_with_progress(src, dst, max_workers=4,desc = ""):
    total_size = calculate_total_size(src)
    copied_size_total = Value(ctypes.c_uint64, 0)
    lock = multiprocessing.Lock()

    with tqdm(total=total_size, unit="B", unit_scale=True, desc=desc) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {}
            for dirpath, dirnames, filenames in os.walk(src):
                relative_path = os.path.relpath(dirpath, src)
                target_dir = os.path.join(dst, relative_path)
                os.makedirs(target_dir, exist_ok=True)

                for f in filenames:
                    src_file = os.path.join(dirpath, f)
                    dst_file = os.path.join(target_dir, f)
                    future = executor.submit(copy_file_with_progress, src_file, dst_file,copied_size_total,lock)
                    future_to_file[future] = (src_file, dst_file)

            #开启线程复制检查
            while_state = True
            total_count = len(future_to_file)
            completed_count = 0
            while while_state:
                if total_count == completed_count:
                    while_state = False
                pbar.desc = f"{completed_count}/{total_count}-{desc}"
                pbar.n = copied_size_total.value
                pbar.refresh()
                time.sleep(0.5)

                for future in list(future_to_file.keys()):
                    if future.done():
                        src_file, dst_file = future_to_file[future]
                        try:
                            future.result()
                            completed_count += 1
                            future_to_file.pop(future)
                        except Exception as e:
                            print(f"文件 {src_file} 复制失败: {e}")


if __name__ == '__main__':
    copy_folder_with_progress(r"D:\RSI\b",r"D:\RSI\test",max_workers=4,desc="copytest")
