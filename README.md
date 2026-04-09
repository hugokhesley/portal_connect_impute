# Portal de Impute — Connect Group
## Repositório: portal_connect_impute

### Setup

**1. Secrets (`.streamlit/secrets.toml`)**
```toml
gcp_service_account = '''
{conteúdo do credentials.json aqui — copie o arquivo inteiro}
'''

[email]
host     = "smtp.titan.email"
port     = 465
user     = "adm@connectgroup.solutions"
password = "SUA_SENHA"
from     = "Connect Group Portal <adm@connectgroup.solutions>"
```

**2. Deploy no Streamlit Cloud**
- Repositório: `portal_connect_impute` (separado do dashboard)
- Branch: `main`
- Main file: `app.py`

**3. Primeiro acesso**
- Login: `admin`
- Senha: `ConnectAdmin@2026`
⚠️ Crie um novo usuário admin e desative o padrão após o primeiro acesso.

### Hierarquia de perfis
| Perfil | Acesso |
|--------|--------|
| admin | Tudo — pedidos, usuários, fila |
| bko | Toda a fila + atualizar status |
| lider | Pedidos da equipe dele |
| parceiro | Só os seus pedidos |
| vendedor | Só os seus pedidos |

### Abas criadas automaticamente no Sheets
- `PortalUsuarios` — cadastro de usuários
- `PortalPedidos` — todos os pedidos com todos os campos do Radar Blue

### Notificação BKO
Ao cadastrar pedido, email automático vai para:
- adm@connectgroup.solutions
- guthyerre.silva@connectbrasil.tech
- bko2@connectbrasil.tech
