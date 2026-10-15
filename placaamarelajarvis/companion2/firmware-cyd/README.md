# Atlas Matematica para ESP32-2432S028R

Tutor adaptativo de matematica para bacharelado na Cheap Yellow Display.

- DeepSeek gera explicacoes, formulas, graficos e questoes.
- Dificuldade muda conforme acertos, erros, sequencia e dominio.
- Pausar e continuar preservam o topico e o nivel.
- Conquistas ficam na flash.
- Historico detalhado: `/atlas/matematica.csv` no microSD.

```powershell
arduino-cli compile --fqbn esp32:esp32:esp32 firmware-cyd/atlas_cyd
arduino-cli upload -p COM15 --fqbn esp32:esp32:esp32 firmware-cyd/atlas_cyd
```

A chave DeepSeek deve ser injetada no build e nao registrada no codigo-fonte.
