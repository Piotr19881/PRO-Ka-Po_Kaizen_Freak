' launch_hidden.vbs
' Run a program hidden. Usage (from cmd):
'   cscript //nologo launch_hidden.vbs "C:\path\to\python.exe" "C:\path\to\main.py"
'
Optionally provide any executable and its first argument (we pass only two args here: exe and single arg).

Set WshShell = CreateObject("WScript.Shell")
exe = ""
arg1 = ""
If WScript.Arguments.Count >= 1 Then exe = WScript.Arguments(0)
If WScript.Arguments.Count >= 2 Then arg1 = WScript.Arguments(1)
If exe = "" Then
    WScript.Echo "ERROR: missing exe argument"
    WScript.Quit 2
End If

' Quote the arguments to be safe
cmd = """" & exe & """" & " " & """" & arg1 & """"
WshShell.Run cmd, 0, False
