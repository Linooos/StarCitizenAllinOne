import ctypes
import sys

import win32api
import re
import common


def get_user_sid():
    # 获取当前用户名
    username = win32api.GetUserName()

    # 初始化缓冲区
    sid = ctypes.create_string_buffer(256)
    sid_size = ctypes.c_ulong(256)
    domain_name = ctypes.create_unicode_buffer(256)
    domain_size = ctypes.c_ulong(256)
    sid_name_use = ctypes.c_ulong()

    # 调用 Windows API 获取 SID
    result = ctypes.windll.advapi32.LookupAccountNameW(
        None,
        username,
        sid,
        ctypes.byref(sid_size),
        domain_name,
        ctypes.byref(domain_size),
        ctypes.byref(sid_name_use)
    )

    if result == 0:
        raise ctypes.WinError()

    # 转换 SID 为可读格式
    sid_str = ctypes.c_wchar_p()
    ctypes.windll.advapi32.ConvertSidToStringSidW(
        sid,
        ctypes.byref(sid_str)
    )

    return sid_str.value

def set_startup_plan(exe_path):
    user_sid = get_user_sid()

    xml_plan_string =f"""\
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user_sid}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT72H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell</Command>
      <Arguments>{exe_path}</Arguments>
    </Exec>
  </Actions>
</Task>
    """

    xml_path = "start_up_plan.xml"

    with open(xml_path, 'w') as script_file:
            script_file.write(xml_plan_string)

if __name__ == '__main__':
    set_startup_plan(r"D:\WinUsers\abc67\Documents\GitHub\StarCitizenAllinOne\user.py")


