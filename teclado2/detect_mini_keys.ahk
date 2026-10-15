#NoEnv
SetBatchLines -1

MsgBox, 262144, Detector de Teclas, Pressione as 4 teclas do mini teclado uma por uma.`nAs teclas detectadas aparecerão aqui.`n`nClique OK pra iniciar a detecção.

keys_detected := ""
key_count := 0

; Detecta qualquer tecla
~*::
{
    global keys_detected, key_count
    key := A_ThisHotkey
    key_count++
    keys_detected .= key_count . ": " . key . "`n"

    ToolTip, Teclas detectadas:`n%keys_detected%

    if (key_count >= 4) {
        Sleep, 1000
        ToolTip
        MsgBox, 262144, Teclas Detectadas, %keys_detected%
        ExitApp
    }
    return
}
