#NoEnv
SetBatchLines -1

; Atalhos para o mini teclado (4 teclas)
; Os códigos das teclas são suposições comuns (F13-F16)
; Se não funcionar, execute detect_mini_keys.ahk primeiro

; KEY1 -> Grokbot
F13::
{
    Run, start https://grokbot.com
    return
}

; KEY2 -> ChatGPT
F14::
{
    Run, start https://chat.openai.com
    return
}

; KEY3 -> Claude
F15::
{
    Run, start https://claude.ai
    return
}

; KEY4 -> Grok na web
F16::
{
    Run, start https://grok.com
    return
}

; Alternativas (alguns teclados usam estes códigos)
; Descomente se as teclas acima não funcionarem:

/*
; Se as teclas forem numeradas 1-4:
1::Run, start https://grokbot.com
2::Run, start https://chat.openai.com
3::Run, start https://claude.ai
4::Run, start https://grok.com

; Se as teclas forem Page Up, Page Down, etc:
PgUp::Run, start https://grokbot.com
PgDn::Run, start https://chat.openai.com
Home::Run, start https://claude.ai
End::Run, start https://grok.com
*/
