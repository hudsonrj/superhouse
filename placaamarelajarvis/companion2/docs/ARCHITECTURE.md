# Arquitetura do Companion2

## 1. Dispositivo

O ESP32 executa tudo que precisa continuar disponivel sem internet:

- maquina de estados dos ciclos de acompanhamento;
- interface de toque com uma pergunta por vez;
- verificacao objetiva de risco e atalhos de apoio humano;
- perfil, consentimentos e ciclo ativo em NVS;
- captura temporaria de camera e audio;
- reducao de ruido e cancelamento de eco;
- indicadores visuais de uso dos sensores;
- fila local de eventos sem conteudo bruto de audio ou imagem.

## 2. Servico multimodal

Tarefas pesadas ficam em um servico separado, acessado apenas quando o usuario
autorizar:

- fala para texto em portugues;
- texto para fala em portugues;
- OCR de rotulos e embalagens;
- leitura de codigo de barras e QR;
- descricao de cena;
- extracao de sinais observaveis para um check-in, sem classificar humor como
  verdade.

O servico deve devolver dados estruturados com confianca, limitacoes e uma
pergunta de confirmacao. A maquina de seguranca local decide o proximo passo e
nao pode ser substituida pelo modelo multimodal.

## 3. Fontes de contexto

- toque: estado e escolhas declarados pelo usuario;
- microfone: fala enviada somente durante uma sessao iniciada pelo usuario;
- camera: uma captura por autorizacao fisica;
- IMU: movimento ou ausencia de movimento, nunca conclusao emocional;
- agenda e rotina: apenas com permissao separada;
- sensores basicos: temperatura do chip nao representa temperatura corporal.

Ordem de prioridade do produto:

1. toque e escolha declarada pelo usuario;
2. contexto objetivo de ambiente e rotina;
3. audio ou imagem autorizados para a pergunta atual;
4. inferencias do modelo, sempre apresentadas como incertas e confirmaveis.

## 4. Recursos adicionais

Recursos que aproveitam melhor a placa atual:

- IMU QMI8658 para gesto de levantar o aparelho e mudancas grandes de movimento,
  sem classificar emocao, queda ou emergencia por conta propria;
- microSD para exportacao manual de um resumo, com criptografia e consentimento,
  sem gravacao continua de voz ou imagem;
- Bluetooth ou Wi-Fi para acionar um contato de confianca somente depois da
  confirmacao do usuario, salvo um plano de emergencia previamente configurado;
- processamento local do ESP-SR para reducao de ruido, cancelamento de eco e
  comandos limitados quando houver suporte adequado ao idioma.

Melhorias fisicas recomendadas para uma revisao do hardware:

- motor de vibracao com driver para o modo silencioso;
- LED dedicado e eletricamente ligado a alimentacao da camera ou microfone;
- obturador fisico para a camera e chave de corte do microfone;
- bateria monitorada, para que falta de energia nao seja confundida com ausencia
  de resposta do usuario.

## 5. Medicamentos

O fluxo recomendado e:

1. ler codigo de barras ou QR;
2. extrair texto da embalagem e do rotulo;
3. consultar uma fonte oficial configurada;
4. mostrar nome, concentracao e forma farmaceutica como dados a confirmar;
5. exigir confirmacao do usuario;
6. encaminhar duvidas de dose, interacao ou troca a um farmaceutico ou medico.

Uma imagem de comprimido solto nao e identificacao suficiente.

## 6. Evolucao prevista

1. diagnostico local de tela, toque, camera, microfones e alto-falante;
2. migracao do fluxo deterministico do primeiro Companion;
3. API local com contratos JSON para voz, visao e OCR;
4. historico minimo e criptografado, opt-in;
5. testes de falha de rede, revogacao de consentimento e emergencia.
