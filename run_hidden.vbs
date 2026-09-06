   Set WshShell = CreateObject("WScript.Shell")
   WshShell.Run """" & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\Start_With_AutoUpdate.bat""", 0, False