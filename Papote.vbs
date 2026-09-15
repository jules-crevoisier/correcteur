' Demarre le correcteur sans laisser de fenetre noire ouverte.
Set shell = CreateObject("WScript.Shell")
dossier = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = dossier
shell.Run """" & dossier & "\.venv\Scripts\pythonw.exe"" -m papote", 0, False
