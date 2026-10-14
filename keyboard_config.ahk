#NoEnv
SetBatchLines -1

; Detectar qual tecla do mini teclado foi pressionada
; Primeiro, descubra o código da tecla com este script de detecção

^+d::  ; Ctrl+Shift+D para iniciar detecção
{
    MsgBox, 4, Key Detection, Pressione qualquer tecla do mini teclado. Será mostrado seu código.
    ifMsgBox No
        return

    KeyWait  ; Espera pela próxima tecla
    MsgBox, % "Código da tecla: " A_PriorKey "`nCódigo ASCII: " Ord(A_PriorKey)
    return
}
