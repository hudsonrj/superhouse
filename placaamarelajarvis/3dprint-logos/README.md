# Modelos 3MF para Anycubic Kobra X

## Casa de férias (ferias.png)

Arquivo: **`Casa_Ferias_KobraX.3mf`**

Casa + salão + jardim com piscina, escala ~**1:150**. Sem carros e sem árvores. Mobília em relevo: camas, sofás, mesas com cadeiras, cozinha, banheiros, pingue-pongue, espreguiçadeiras, mesas de piquenique.

| | |
|---|---|
| Tamanho | ~235 × 144 × 13 mm |
| Cores ACE | gramado, pisos/deck, paredes, móveis |
| Sem suporte | imprime deitado |

---

## Planta do apartamento (1:100)

Arquivo: **`Planta_Apartamento_KobraX.3mf`**

Planta em escala **1:100** traçada a partir de `fl.jpg`. Só cômodos e paredes — sem mobília.

| | |
|---|---|
| Tamanho | ~112 × 99 × 12 mm |
| Piso | 1,6 mm |
| Paredes | 1,5 mm de espessura, 12 mm de altura |
| Portas | vãos reais (cozinha, WC, quarto, banheiros, sala→varanda) |
| Janelas | peitoril baixo no quarto e na suíte |
| Varanda | curva da planta + guarda-corpo baixo |
| Nomes | relevo no piso: COZINHA, SALA, QUARTO, SUITE, BANHO, VARANDA… |
| Cores | piso bege + paredes pretas (2 slots ACE) |

Perfil: PLA, camada 0,20 mm, 3 paredes, 15% infill, **sem suporte**. Piso no slot 1 (claro), paredes no slot 2 (preto). Uma cor só também funciona.

Fonte: `fl.jpg`. Gerador: `build_planta_3mf.py`.

---

# Grok + xAI — placa 3MF para Anycubic Kobra X

Arquivo pronto para fatiar: **`Grok_xAI_KobraX.3mf`**

Placa de mesa com o mark oficial do Grok (fev/2025), o wordmark **Grok** e o monograma geométrico da **xAI**. Três peças no mesmo objeto para impressão em duas cores no ACE.

## Modelo

| | |
|---|---|
| Tamanho | ~179 × 64 × 3,6 mm |
| Volume da Kobra X | 260 × 260 × 260 mm (cabe com folga) |
| Base | 3,0 mm, cantos R7 mm, PLA preto |
| Logos em relevo | 0,8 mm visível + 0,2 mm de sobreposição na base |
| Bico | 0,4 mm (padrão da Kobra X) |
| Cores | 2 (preto + branco). Os logos são peças separadas se quiser 3 cores. |

## Como imprimir

1. Abra o `.3mf` no **Anycubic Slicer Next**.
2. Impressora: **Kobra X 0.4 mm**.
3. Filamento sugerido: PLA.
4. Associe as peças:
   - `Base (preto)` → slot 1, PLA preto
   - `Logo Grok` → slot 2, PLA branco
   - `Logo xAI` → slot 2 (mesmo branco) ou slot 3 se quiser outra cor
5. Fatie e envie pela nuvem, LAN ou USB.

Se o slicer importar tudo como um único sólido, use pintura de cor / atribuição por peça. Em uma cor só o relevo de 0,8 mm ainda lê os logos.

## Perfil sugerido (Kobra X, bico 0,4 mm)

- Altura de camada: **0,20 mm** (o relevo vira 4 camadas)
- Paredes: 3
- Preenchimento: 15% gyroid
- Suporte: nenhum
- Brim: opcional 3 mm se a primeira camada falhar
- Mesa: 60 °C · bico: 220 °C (PLA)
- Sem overhangs — imprime deitado, face dos logos para cima

## Arquivos

- `Grok_xAI_KobraX.3mf` — modelo
- `preview_top.png` — vista de cima
- `preview_iso.png` — relevo em perspectiva
- `build_grok_xai_3mf.py` — gerador (re-rode se quiser mudar tamanho)

Grok e xAI são marcas da xAI / SpaceXAI. Uso pessoal / fã.
