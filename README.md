# Karaokê Neves

Sistema de karaokê com uma tela conectada à TV/projetor e controles para celular.
A TV mostra o QR Code enquanto aguarda e troca para o vídeo durante a música; os
convidados usam o celular para adicionar músicas, ver a fila e pular a música.
QR Code e vídeo compartilham uma única janela Chromium em tela cheia e modo
quiosque para reduzir o uso de memória no Raspberry Pi. O controle para celular
tem fila pesquisável, permite reordenar ou remover pedidos e pede confirmação
antes de pular a música que está tocando. Enquanto uma música toca, o player
pré-busca os vídeos das músicas na fila e mostra a próxima escolha sobre o vídeo.
Na primeira visita, o controle pede um nome e o guarda no navegador do celular;
os pedidos seguintes aparecem na fila como `música - nome`.

## Requisitos

- Python 3.10 ou superior
- Chromium e uma sessão gráfica para a tela de reprodução
- Conexão à internet para pesquisar e reproduzir vídeos do YouTube

## Instalação

### Linux e Raspberry Pi

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r req.txt
python -m playwright install chromium
```

Se a distribuição precisar de bibliotecas de sistema para o navegador, instale
as dependências do Chromium conforme a documentação da distribuição. Também é
possível usar um Chromium já instalado definindo `KARAOKE_BROWSER_EXECUTABLE`
no arquivo `.env` (por exemplo, `/usr/bin/chromium`).

Inicie o sistema a partir da sessão gráfica:

```bash
./start_karaoke.sh
```

O script usa `venv/bin/python` quando o ambiente virtual existe; caso contrário,
usa `python3`. Ele não atualiza o Git, espera conexão externa nem encerra
processos de outras aplicações.

### Windows

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r req.txt
.\venv\Scripts\python.exe -m playwright install chromium
.\start_karaoke.bat
```

O launcher também usa o ambiente `venv` se existir; caso contrário, usa `python`
do `PATH`. Alternativamente, execute `python app.py`.

## Configuração

Copie `.env.example` para `.env` para ajustar portas e navegador. Em geral, os
valores padrão são suficientes. Se a detecção automática escolher o IP de rede
errado, informe em `KARAOKE_HOST` o endereço do computador na rede local. O QR
Code apontará para a tela de controle nesse endereço.

O celular e o computador do karaokê precisam estar na mesma rede. Libere a
porta de controle (5000 por padrão) no firewall, se necessário. A fila fica em
`data/karaoke.sqlite3` e continua disponível depois de reiniciar o programa.
Defina `KARAOKE_DB_PATH` para mudar o local do arquivo.

## Como funciona

- `entry_screen`: serve a tela inicial e gera o QR Code para os controles.
- `web_interface`: oferece a interface móvel via Socket.IO.
- `music_queue`: valida e mantém a fila e a música atual em SQLite.
- `video_player`: busca vídeos, abre uma janela Chromium em tela cheia e modo
  quiosque, pré-busca os vídeos da fila, alterna a mesma página entre QR Code e
  vídeo e processa término e skip da música.
- `app.py`: inicia e supervisiona os serviços; se um serviço falhar, encerra os
  demais. `Ctrl+C` encerra o sistema.

As APIs internas escutam apenas em `127.0.0.1`; o controle móvel e a tela do QR
Code escutam na rede local.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem persistência e operações da fila, validação de API, erros de
comunicação, endpoints de reprodução, geração do QR Code e supervisão dos
serviços. Eles não iniciam o Chromium nem acessam o YouTube.
