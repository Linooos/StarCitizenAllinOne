import os,sys
current = ''
if hasattr(sys,'_MEIPASS'):
    current = os.path.dirname(sys.argv[0])
else:
    current = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current)

import user
import common
import subprocess
import tkinter as tk
from tkinter import filedialog
from shutil import get_terminal_size
import ctypes
import time

def format_screen(strInfo):
    columns, rows = get_terminal_size()
    print("\n" * rows)
    print(strInfo)

def create_diff_vhdx(parent_vhdx, diff_vhdx,name):
    # 创建 diskpart 脚本
    diskpart_script = f"""\
create vdisk file="{diff_vhdx}" parent="{parent_vhdx}"
    """
    script_path = "create_diff_vhdx_script.txt"

    with open(script_path, 'w') as script_file:
        script_file.write(diskpart_script)

    # 运行 diskpart 脚本
    #os.system(f'diskpart /s \"{os.path.join(current,script_path)}\"')
    common.run_command(['diskpart', '/s', os.path.join(current,script_path)])

    # 删除临时 diskpart 脚本
    os.remove(script_path)

    print(f"差分 VHDX 文件已创建并格式化：{diff_vhdx}")

def switch_mount_vhdx_to_paths(vhdx_path_list,des_path,mount = False,run = True):
    vhdxs_path_strings = ""
    for i in range(len(vhdx_path_list)):
        if i == 0:
            vhdxs_path_strings += f"\"{vhdx_path_list[i]}\""
            continue
        vhdxs_path_strings += f",\"{vhdx_path_list[i]}\""

    if not des_path[-1] == "\\":
        des_path += "\\"

    power_script1 = f""" 
$vhdxPaths = @({vhdxs_path_strings})
$mountBasePath = "{des_path}"
    """
    power_script2 = """
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

foreach ($vhdxPath in $vhdxPaths) {
    $vhdxName = [System.IO.Path]::GetFileNameWithoutExtension($vhdxPath)
    $mountPoint = Join-Path -Path $mountBasePath -ChildPath $vhdxName
"""
    power_script3="""
    if (Test-Path -Path $mountPoint -PathType Container) {
        mountvol $mountPoint /D | Out-Null
    } else {
        New-Item -ItemType Directory -Path $mountPoint | Out-Null
    }
"""
    power_script4="""
    Dismount-DiskImage -ImagePath $vhdxPath -Confirm:$false | Out-Null
    
    """
    power_script5 = """
    $VirtualDisk = Mount-DiskImage -ImagePath $vhdxPath -NoDriveLetter -PassThru
    $Disk = Get-Disk -Number $VirtualDisk.Number

    $PartitionObject = Get-Partition -DiskNumber $Disk.DiskNumber | Where-Object { $_.Size -gt 10MB } | Select-Object -First 1

    Add-PartitionAccessPath -InputObject $PartitionObject -AccessPath $mountPoint

    Write-Host "VHDX:$vhdxPath  $mountPoint"
}
    """
    script_path = "mount_vhdx_script.ps1"

    with open(script_path, 'w') as script_file:
        if mount:
            script_file.write(power_script1+power_script2+power_script3+power_script4+power_script5)
        else:
            script_file.write(power_script1+power_script2+power_script4+"\n}")
    if run:
        #os.system(f'powershell \"{os.path.join(current, script_path)}\"')
        common.run_command(['powershell', os.path.join(current, script_path)])
        # 删除临时 diskpart 脚本
        os.remove(script_path)
        if not mount:
            os.rmdir(des_path)

def create_vhdx(vhdx_path, size_in_mb,name):
    '''
    创建vhdx，默认创建可变大小
    :param vhdx_path: vhdx路径
    :param size_in_mb: 文件预分配大小(MB)
    :return: -
    '''
    # 创建 disk part 脚本
    disk_part_script = f"""
    create vdisk file="{vhdx_path}" type=expandable maximum={size_in_mb}
    select vdisk file="{vhdx_path}"
    attach vdisk
    create partition primary
    format fs=ntfs quick label="{name}"
    detach vdisk
    exit
    """
    script_path = "create_vhdx_script.txt"

    with open(script_path, 'w') as script_file:
        script_file.write(disk_part_script)

    # 运行 diskpart 脚本
    #os.system(f'diskpart /s \"{os.path.join(current, script_path)}\"')
    common.run_command(['diskpart', '/s', os.path.join(current,script_path)])

    # # 删除临时 diskpart 脚本
    os.remove(script_path)

    print(f"VHDX 文件已创建并格式化：{vhdx_path}")

def add_startUp_plan(xml_path):
    # PowerShell 脚本
    powershell_script = f"""
# 定义触发器，在用户登录时触发
$trigger = New-ScheduledTaskTrigger -AtLogon

# 定义动作
$action = New-ScheduledTaskAction -Execute "powershell" -Argument "{xml_path}"

# 指定任务的用户 ID（SID）
$userid = "{user.get_user_sid()}"  # 替换为实际的用户 SID

# 注册计划任务，使用指定的触发器、动作和用户 SID
Register-ScheduledTask -TaskName "START_UP_STARCITIZEN" -Trigger $trigger -Action $action -Description "Mount game data vdisk while user login" -User $userid -RunLevel Highest

# 禁用“仅在交流电源时使用”选项
$task = Get-ScheduledTask -TaskName "START_UP_STARCITIZEN"
$task.Settings.DisallowStartIfOnBatteries = $false
$task.Settings.StopIfGoingOnBatteries = $false
Set-ScheduledTask -TaskName "START_UP_STARCITIZEN" -Settings $task.Settings

    """

    # 创建 PowerShell 脚本文件
    script_file = "import_task.ps1"
    with open(script_file, 'w') as file:
        file.write(powershell_script)

    # 运行 PowerShell 脚本
    result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", script_file], capture_output=True,
                            text=True)
    os.remove(script_file)
    # 输出结果

if __name__ == '__main__':
    if common.is_admin():
        print("已在管理员权限下运行\n")
    else:
        print("需要管理员权限\n")
        # ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, ' '.join(sys.argv), None, 1)
        exit(1)



    try:
        format_screen("如果你有同时游玩pu，ptu，eptu的需求，那么这个工具可以为你省去两个本体的空间占用，同时不需要再文件夹改名然后下载更新。\n"
                      "一个本体，三种服务器平行存在，更新互不干扰。\n"
                      "！！！注意！！！\n"
                      "如果第一次运行请在管理员powershell中运行 Set-Executionpolicy Remotesigned"
                      "部署本脚本需要预留一个本体的空间，供复制文件使用，在150GB左右预留\n"
                      "需要管理员权限\n"
                      "脚本会在RSI路径下创建一些文件，请勿删除,starcitizen_backup文件夹为脚本备份，如果运行失败，将其改回原名\n"
                      "运行脚本时请关闭启动器和游戏数据目录的资源管理器，否则会出现无法访问数据的情况\n"
                      "脚本会添加一个名为START_UP_STARCITIZEN的计划任务，请勿删除\n")
        os.system("pause")
        format_screen("请选择：StarCitizen_Launcher.exe")
        root = tk.Tk()
        root.withdraw()
        f_path = filedialog.askopenfilename(title="请选择：StarCitizen_Launcher.exe")
        f_path = f_path.replace("/", "\\")

        path = os.path.dirname(f_path)
        if not ('LIVE' == os.path.basename(path) or 'PTU' == os.path.basename(path) or 'EPTU' == os.path.basename(path)):
            format_screen("文件无法识别")
            os.system("pause")
            exit(1)
        game_server = os.path.basename(path)

        path = os.path.dirname(os.path.dirname(path))
        if not 'RSI' == os.path.basename(path):
            format_screen("文件无法识别")
            os.system("pause")
            exit(1)

        # 修改原文件夹为backup
        common.rename_folder(os.path.join(path, "starcitizen"), "starcitizen_backup")
        print(f"文件夹已重命名：starcitizen_backup")

        # 创建vhdx
        original_vhdx_path = os.path.join(path, "original.vhdx")
        create_vhdx(original_vhdx_path, 204800,"starcitizen") # 200GB

        # 挂载vhdx到original文件夹
        switch_mount_vhdx_to_paths([original_vhdx_path],path,True)
        # 拷贝文件到vhdx
        # for r,d,f in os.walk(path):
        #     for file in f:
        #         os.system(f"attrib -r {os.path.join(r,file)}")
        common.copy_folder_with_progress(os.path.join(path, "starcitizen_backup",game_server),os.path.join(path, "original"),max_workers=8,desc="拷贝星际公民数据到vhdx")

        # 卸载vhdx
        switch_mount_vhdx_to_paths([original_vhdx_path], os.path.join(path, "original"), False)
        time.sleep(4)
        # 新建差分
        create_diff_vhdx(original_vhdx_path, os.path.join(path, "LIVE.vhdx"),"LIVE")
        create_diff_vhdx(original_vhdx_path, os.path.join(path, "PTU.vhdx"),"PTU")
        create_diff_vhdx(original_vhdx_path, os.path.join(path, "EPTU.vhdx"),"EPTU")

        # 新建路径
        common.check_and_create_directory(os.path.join(path, "starcitizen"))

        # 挂载差分
        list_vhdxs = [os.path.join(path, "PTU.vhdx"),os.path.join(path, "EPTU.vhdx"),os.path.join(path, "LIVE.vhdx")]
        switch_mount_vhdx_to_paths(list_vhdxs, os.path.join(path, "starcitizen"), True)



        switch_mount_vhdx_to_paths(list_vhdxs, os.path.join(path, "starcitizen"), True,False)
        common.copy_file(os.path.join(current,"mount_vhdx_script.ps1"),os.path.join(path,"start_up.ps1"))
        os.remove("mount_vhdx_script.ps1")

        user.set_startup_plan(os.path.join(path,"start_up.ps1"))
        common.copy_file(os.path.join(current, "start_up_plan.xml"), os.path.join(path, "start_up_plan.xml"))
        os.remove("start_up_plan.xml")

        # 添加自启动到计划管理
        add_startUp_plan(os.path.join(path, "start_up_plan.xml"))
    except Exception as e:
        print(e)
        os.system("pause")







