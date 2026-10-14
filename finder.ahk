#NoEnv
SetBatchLines -1

MsgBox, 0, Detector, Pressione cada uma das 4 teclas do mini teclado. Os códigos aparecerão aqui.`n`nClique OK para iniciar.

keys := []
MsgBox, 0, Tecla 1, Pressione a PRIMEIRA tecla agora!
Input, key1, L1
keys.Push("Tecla 1: " . key1)

MsgBox, 0, Tecla 2, Pressione a SEGUNDA tecla agora!
Input, key2, L1
keys.Push("Tecla 2: " . key2)

MsgBox, 0, Tecla 3, Pressione a TERCEIRA tecla agora!
Input, key3, L1
keys.Push("Tecla 3: " . key3)

MsgBox, 0, Tecla 4, Pressione a QUARTA tecla agora!
Input, key4, L1
keys.Push("Tecla 4: " . key4)

msg := ""
for index, value in keys
    msg .= value . "`n"

MsgBox, 0, Códigos Detectados, %msg%`n`nEnvie essa info pro Claude!
