#NoEnv
SetBatchLines -1

; Detecta qualquer tecla pressionada e mostra seu código
~*::
{
    key := A_ThisHotkey
    MsgBox, Tecla pressionada: %key%`nDesça detectar outras teclas clicando OK
    return
}
