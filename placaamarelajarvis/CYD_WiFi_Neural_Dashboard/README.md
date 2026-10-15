# Acompanhante Adaptativo CYD

Firmware Arduino para a placa ESP32-2432S028R (Cheap Yellow Display) que oferece apoio imediato de regulacao emocional, cognitiva e comportamental por toques.

O dispositivo nao diagnostica, nao altera medicamentos e nao substitui atendimento medico, psicologico, psiquiatrico, cuidadores ou servicos de emergencia.

## Fluxo principal

A tela `APOIO` abre diretamente com opcoes grandes:

- ajuda agora;
- sobrecarga;
- reuniao;
- dificuldade para pensar;
- impulso;
- ansiedade;
- tristeza ou desanimo;
- falta de energia;
- organizacao;
- silencio;
- companhia.

Depois de um toque, o firmware:

1. confirma se o local e fisicamente seguro;
2. estima o desconforto com uma escala de 1 a 5;
3. pergunta qual capacidade esta mais comprometida quando isso for util;
4. em niveis leves ou moderados, registra local, companhia, possibilidade de sair, antecedente imediato e urgencia;
5. oferece uma unica acao curta;
6. verifica se a intensidade melhorou, permaneceu igual ou piorou;
7. prepara contato humano ou atendimento presencial quando a seguranca nao pode ser confirmada;
8. cria um resumo antes do encerramento.

Os controles `VOLTAR`, `PAUSA`, `SILENC`, `GUIA` e `FIM` permanecem disponiveis durante o ciclo. Um ciclo ativo e salvo na memoria NVS e pode ser retomado depois de reiniciar a placa.

As orientacoes essenciais sao locais e continuam funcionando sem Wi-Fi e sem IA externa.

## Perfil adaptativo

Com a placa conectada, abra o endereco IP mostrado na tela em um aparelho da mesma rede. O portal local permite informar:

- nome, idade e forma de tratamento;
- neurodivergencias conhecidas ou suspeitas;
- condicoes relevantes;
- sensibilidades, sinais iniciais e sinais de agravamento;
- gatilhos e situacoes de estresse;
- estrategias que ajudam ou pioram;
- comunicacao e grau de autonomia preferidos;
- frases que acalmam e frases a evitar;
- pessoa e telefone de confianca;
- tratamentos informados, rotina, objetivos e limites.

Medicamentos e tratamentos sao apenas registrados como contexto. O firmware nao orienta alteracao de dose ou interrupcao.

## Consentimento e privacidade

Existem tres permissoes independentes, desligadas por padrao:

- `APRENDER`: registra contagens locais para adaptar o acompanhamento;
- `ALERTAS`: mostra avisos de possivel aumento de sobrecarga;
- `NUVEM`: reserva permissao para uma integracao externa opcional. O fluxo adaptativo atual nao envia o perfil.

O perfil e o ciclo ficam na NVS do ESP32 ate o usuario usar `APAGAR DADOS`. A exclusao exige dois toques na tela. O portal tambem oferece exclusao.

O portal embarcado usa HTTP e deve ser acessado somente em uma rede local confiavel. Qualquer pessoa na mesma rede que conheca o IP pode tentar acessa-lo. O log em cartao SD permanece desativado por padrao (`ENABLE_SD_LOG 0`).

O botao de apoio humano mostra o contato configurado. Como esta placa nao possui modem celular, ela nao realiza a ligacao sozinha. No portal aberto em um telefone, o link de contato usa `tel:`.

Esta revisao de hardware oferece texto, cores e toque. Audio e vibracao exigem modulos adicionais e nao sao anunciados pela interface quando o hardware nao existe.

## Credenciais

O repositorio nao contem chave de API nem senha Wi-Fi. Para compilar com uma chave externa, defina antes do sketch:

```cpp
#define DEEPSEEK_API_KEY "sua-chave"
```

A regulacao principal nao depende dessa chave. A rede e configurada por SmartConfig ou pela tela `WIFI`.

## Hardware alvo

- ESP32-2432S028R
- TFT ILI9341 320x240 via SPI
- touch XPT2046 resistivo via SPI
- backlight no GPIO 21
- LDR no GPIO 34
- LED RGB nos GPIOs 4, 16 e 17

## Compilacao

1. Instale o suporte a ESP32 na Arduino IDE.
2. Abra `CYD_WiFi_Neural_Dashboard.ino`.
3. Selecione `ESP32 Dev Module`.
4. Use flash de `4MB`, particao `Default 4MB` e PSRAM desativada.
5. Grave pela USB.

O sketch usa apenas bibliotecas presentes no core ESP32.

## Touch

Na primeira inicializacao desta versao, siga os tres alvos de calibracao. Se necessario, force uma nova calibracao alterando temporariamente:

```cpp
#define FORCE_TOUCH_CALIBRATION true
```
