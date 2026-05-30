#!/usr/bin/env python3
"""
WasFit Instagram Publisher
Publica os 14 posts automaticamente via Meta Graph API.

USO:
  python3 wasfit_publisher.py             # mostra próximo post agendado
  python3 wasfit_publisher.py --publish   # publica o post do dia atual
  python3 wasfit_publisher.py --all       # publica todos os posts pendentes
  python3 wasfit_publisher.py --test      # testa conexão com a API
"""

import os, sys, json, time, base64, requests
from datetime import datetime, timezone
from pathlib import Path

# ── CONFIGURAÇÃO — lê credenciais do .env ────────────────────────────────────
def load_env():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return {}  # GitHub Actions usa Secrets via os.environ
    env = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

_env = load_env()
# Variáveis de ambiente têm prioridade (GitHub Actions), .env como fallback
INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID") or _env.get("INSTAGRAM_USER_ID", "")
PAGE_ID           = os.environ.get("PAGE_ID")           or _env.get("PAGE_ID", "")
ACCESS_TOKEN      = os.environ.get("ACCESS_TOKEN")      or _env.get("ACCESS_TOKEN", "")
SUPABASE_URL      = os.environ.get("SUPABASE_URL")      or _env.get("SUPABASE_URL", "")
SUPABASE_KEY      = os.environ.get("SUPABASE_SECRET_KEY") or _env.get("SUPABASE_SECRET_KEY", "")

if not INSTAGRAM_USER_ID or not ACCESS_TOKEN:
    print("❌ Credenciais não encontradas. Configure o .env ou os GitHub Secrets.")
    sys.exit(1)

POSTS_DIR = Path(__file__).parent / "Posts Instagram"
API_BASE  = "https://graph.facebook.com/v19.0"
SB_BUCKET = f"{SUPABASE_URL}/storage/v1/object/public/wasfit-posts"

# ── CALENDÁRIO DOS 14 POSTS ───────────────────────────────────────────────────
POSTS = [
    {
        "num": "01",
        "date": "2026-05-30",
        "hora": "18:30",
        "image": "post01_v5_30mai.png",
        "caption": """Em 2026, o lead que não recebe resposta em 5 minutos já foi para o concorrente. 📲

A boa notícia: a IA já resolve isso por você — 24h por dia, 7 dias por semana, sem hora extra, sem folga.

A WasFit nasceu exatamente pra isso: colocar a sua academia no piloto automático sem perder o toque humano que faz o aluno ficar.

Pergunta: quanto tempo sua equipe leva pra responder um lead que chega às 22h?

👇 Comenta aqui embaixo.

#WasFit #AutomacaoParaAcademias #IAnoWhatsApp #GestaoDeAcademia #FitnessTech #AtendimentoAutomatico #LeadsAcademia"""
    },
    {
        "num": "02",
        "date": "2026-06-02",
        "hora": "08:00",
        "image": "post02_v5_02jun.png",
        "caption": """Você investe em tráfego, o lead chega… e vai embora em silêncio. 🤫

Os 3 motivos mais comuns:

❌ Demora no primeiro atendimento
❌ Ninguém faz follow-up depois do "vou pensar"
❌ Sem controle de quem foi contactado ou não

O resultado? Dinheiro jogado fora todo mês.

A WasFit mapeia cada lead em um kanban visual e garante que nenhum contato seja esquecido.

Arrasta pro lado pra ver como funciona na prática 👉

#GestaoDeLeads #VendasParaAcademia #KanbanDeLeads #WasFit #AtendimentoRapido #AcademiaDeResultado #GestorDeAcademia"""
    },
    {
        "num": "03",
        "date": "2026-06-04",
        "hora": "12:00",
        "image": "post03_v5_04jun.png",
        "caption": """Quantos leads estão parados esperando um follow-up da sua equipe agora? 🤔

Com o Kanban da WasFit, sua equipe enxerga cada lead em tempo real — desde o primeiro contato até a matrícula fechada.

✅ Sem planilha
✅ Sem post-it
✅ Sem "achei que você tinha respondido"

Uma visão clara do funil = mais conversões, menos estresse.

Comenta "QUERO VER" e a gente te mostra ao vivo. 👇

#WasFit #KanbanDeLeads #VendasAcademia #CRMParaAcademia #AutomacaoComercial #FitnessTech #GestaoDeVendas"""
    },
    {
        "num": "04",
        "date": "2026-06-06",
        "hora": "17:00",
        "image": "post04_v5_06jun.png",
        "caption": """Spoiler: sim. E está acontecendo agora em academias que já acordaram para a IA. 🤖

Enquanto você dorme:
📩 Leads sendo respondidos
📅 Aulas sendo agendadas
🔔 Follow-ups sendo enviados

Sua recepcionista pode focar no que ela faz de melhor — o acolhimento presencial. O resto, a WasFit resolve.

Salva esse post pra mostrar pro sócio na próxima reunião. 💾

#IA24horas #AutomacaoAcademia #WasFit #InteligenciaArtificial #GestaoFitness #AtendimentoAutomatico #AcademiaInteligente"""
    },
    {
        "num": "05",
        "date": "2026-06-09",
        "hora": "08:00",
        "image": "post05_v5_09jun.png",
        "caption": """Estudos mostram: responder um lead em até 5 minutos aumenta a chance de conversão em até 9x.

Parece simples. Mas quantas academias conseguem isso de verdade?

🔹 Das 6h às 22h → difícil
🔹 Fins de semana e feriados → quase impossível
🔹 Com uma equipe pequena → esquece

A solução não é contratar mais gente. É automatizar o primeiro contato e deixar sua equipe fechar o negócio.

É exatamente isso que a WasFit faz.

Arrasta pra entender o passo a passo 👉

#RegradosCincoMinutos #ConversaoDeLeads #WasFit #VendasAcademia #AutomacaoWhatsApp #GestaoDeAcademia #MarketingFitness"""
    },
    {
        "num": "06",
        "date": "2026-06-11",
        "hora": "12:00",
        "image": "post06_v5_11jun.png",
        "caption": """Disparo em massa feito errado = número bloqueado + reputação destruída. ❌

Feito certo = alunos rematriculam, promoções que vendem, comunicados que chegam. ✅

A WasFit usa a API oficial da Meta para garantir:

📤 Envio para toda a base de uma vez
🎯 Segmentação por perfil de aluno
📊 Relatório de entrega e leitura
🔒 Zero risco de banimento

Sua academia usa disparos em massa hoje? Comenta aqui! 👇

#DisparoEmMassa #WhatsAppMarketing #WasFit #APIOficialMeta #MarketingAcademia #RetencaoDeAlunos #AutomacaoFitness"""
    },
    {
        "num": "07",
        "date": "2026-06-13",
        "hora": "17:00",
        "image": "post07_v5_13jun.png",
        "caption": """Em 2026, o diferencial competitivo não é mais a esteira ou o equipamento — é a experiência do aluno antes mesmo de entrar pela sua porta. 🚪

As academias que crescem hoje têm algo em comum:
⚡ Resposta imediata
📲 Comunicação via WhatsApp
🤖 IA cuidando dos primeiros contatos
📊 Dados de cada lead na palma da mão

Sua academia está nesse grupo — ou ainda depende de planilha e anotação em papel?

Conta pra gente nos comentários! 👇

#FuturoDasAcademias #WasFit #TechFitness #IAparaAcademias #Tendencias2026 #GestorDeAcademia #InovacaoFitness"""
    },
    {
        "num": "08",
        "date": "2026-06-16",
        "hora": "08:00",
        "image": "post08_v5_16jun.png",
        "caption": """Captar um novo aluno custa até 7x mais do que manter um que já está com você. 💸

Então por que a maioria das academias foca só em novos leads e esquece quem está saindo pela porta dos fundos?

A rematrícula começa 30 dias antes do vencimento — não no dia em que o aluno sumiu.

Com a WasFit, você configura um fluxo automático de retenção:

🗓️ Lembrete 30 dias antes
📲 Mensagem personalizada no dia do vencimento
🔁 Follow-up caso não responda

Retém mais, investe menos. Simples assim.

Salva esse post. 💾

#Rematricula #RetencaoDeAlunos #WasFit #GestaoAcademia #AutomacaoFitness #LTV #MarketingAcademia"""
    },
    {
        "num": "09",
        "date": "2026-06-18",
        "hora": "12:00",
        "image": "post09_v5_18jun.png",
        "caption": """Já tentou usar um chatbot genérico na sua academia e ficou uma bagunça? 😅

Isso acontece porque ele não sabe o que é uma aula experimental, não entende de planos mensais vs. semestrais, e muito menos sabe como convencer alguém a manter a consistência nos treinos.

A IA da WasFit é diferente:

🏋️ Treinada para o nicho fitness
💬 Prompts prontos para academia
📋 Fluxos de atendimento testados no setor
🎯 Respostas que geram matrícula, não confusão

Tecnologia que entende o seu negócio.

Acesse wasfit.com.br e veja como funciona.

#WasFit #IAparaFitness #ChatbotAcademia #AtendimentoInteligente #AutomacaoAcademia #TechParaAcademias"""
    },
    {
        "num": "10",
        "date": "2026-06-20",
        "hora": "17:00",
        "image": "post10_v5_20jun.png",
        "caption": """Em 2026, o brasileiro passa mais tempo no WhatsApp do que em qualquer outro app. 📱

E adivinha onde seu lead vai perguntar sobre preço, planos e horários?

No WhatsApp. Sempre.

A pergunta é: o que acontece depois que ele manda a primeira mensagem?

Se a resposta for "a gente vê quando der" — você já perdeu esse lead.

Com a WasFit, esse lead entra num fluxo automático que:
📨 Responde na hora
🗂️ Classifica no kanban
📅 Agenda uma visita ou aula experimental

É o seu WhatsApp trabalhando como canal de vendas de verdade.

Toca no link da bio e testa grátis. 🔗

#WhatsAppMarketing #WasFit #VendasNoWhatsApp #AcademiaDigital #AutomacaoWhatsApp #LeadsAcademia #MarketingFitness"""
    },
    {
        "num": "11",
        "date": "2026-06-23",
        "hora": "08:00",
        "image": "post11_v5_23jun.png",
        "caption": """Reter aluno é mais barato que captar. Mas exige consistência — e é aí que a maioria falha. 👇

As 5 ações que funcionam:

1️⃣ Mensagem de boas-vindas personalizada no dia 1
2️⃣ Check-in automático na primeira semana
3️⃣ Parabenizar o aluno no aniversário
4️⃣ Aviso de vencimento com oferta de renovação antecipada
5️⃣ Mensagem de reativação para quem sumiu há 15 dias

O detalhe: todas essas ações podem ser 100% automatizadas no WhatsApp.

É exatamente o que a WasFit configura pra você.

Salva pra aplicar na sua academia! 💾

#RetencaoDeAlunos #WasFit #GestaoAcademia #AutomacaoWhatsApp #FidelizacaoDeClientes #FitnessTips #GestorDeAcademia"""
    },
    {
        "num": "12",
        "date": "2026-06-25",
        "hora": "12:00",
        "image": "post12_v5_25jun.png",
        "caption": """Quantas vezes o "combinado" ficou perdido no grupo de WhatsApp da equipe? 😅

A WasFit tem um chat interno integrado à plataforma — pra sua equipe se comunicar sem sair do sistema.

✅ Menos ruído nos grupos pessoais
✅ Comunicação ligada ao contexto de cada lead
✅ Todo mundo na mesma página, em tempo real

Porque academia organizada por dentro entrega resultado melhor lá fora.

Quer ver como funciona na prática? Comenta "DEMO" aqui embaixo 👇

#WasFit #ChatInterno #GestaoDeEquipe #ComunicacaoAcademia #AutomacaoAcademia #FeatureWasFit #FitnessTech"""
    },
    {
        "num": "13",
        "date": "2026-06-27",
        "hora": "17:00",
        "image": "post13_v5_27jun.png",
        "caption": """Em maio de 2026, a Meta anunciou planos de IA integrados a todos os seus apps — incluindo WhatsApp. 📡

O canal que já era o mais usado pelos brasileiros ficou ainda mais poderoso para negócios.

O que isso significa na prática para academias:

🤖 IA mais sofisticada no atendimento
📲 Integração ainda mais nativa com WhatsApp Business
🔗 Conexão entre anúncio → atendimento → matrícula cada vez mais fluida

A WasFit já está preparada para essa evolução. Nossa integração com a API oficial da Meta garante que você esteja sempre um passo à frente.

O futuro chegou. Você está dentro ou fora? 🔗 wasfit.com.br

#MetaIA #WhatsAppBusiness #WasFit #APIMetaOficial #InovacaoFitness #Tendencias2026 #IAnoWhatsApp"""
    },
    {
        "num": "14",
        "date": "2026-06-30",
        "hora": "08:00",
        "image": "post14_v5_30jun.png",
        "caption": """Antes de sair contratando qualquer ferramenta, se faz essas perguntas: 📋

✅ Você sabe de onde vêm seus leads hoje?
✅ Sua equipe registra todos os contatos em algum lugar?
✅ Alguém faz follow-up de forma sistemática?
✅ Você tem um fluxo de rematrícula ativo?
✅ Seu WhatsApp responde fora do horário comercial?

Se respondeu NÃO pra 3 ou mais — você precisa de automação agora.

Se respondeu SIM pra tudo — você está pronto pra escalar com a WasFit.

Comenta quantos "sim" você teve! 👇

#WasFit #ChecklistAcademia #AutomacaoAcademia #GestaoDeLeads #WhatsAppAcademia #AcademiaInteligente #GestorDeFitness"""
    },
]

# ── FUNÇÕES ───────────────────────────────────────────────────────────────────

def upload_image_to_imgbb(image_path):
    """Faz upload da imagem para ImgBB e retorna URL pública."""
    # Tenta sem API key primeiro (limite de 32MB, sem chave)
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    resp = requests.post("https://api.imgbb.com/1/upload", data={
        "key": "publico",  # ImgBB aceita uploads anônimos limitados
        "image": img_b64,
    })
    if resp.ok and resp.json().get("success"):
        return resp.json()["data"]["url"]
    raise Exception(f"Upload falhou: {resp.text}")

def upload_image_simple(image_path):
    """Usa URL pública do Supabase se disponível, senão faz upload para Catbox."""
    # Tenta usar URL do Supabase Storage (já upadas, sem precisar de upload)
    if SUPABASE_URL:
        img_name = Path(image_path).name
        url = f"{SB_BUCKET}/{img_name}"
        # Verifica se a URL está acessível
        try:
            r = requests.head(url, timeout=5)
            if r.status_code == 200:
                print(f"  → Usando URL do Supabase Storage")
                return url
        except:
            pass

    # Fallback: upload para Catbox.moe
    with open(image_path, "rb") as f:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": f}
        )
    if resp.ok and resp.text.strip().startswith("https://"):
        return resp.text.strip()
    raise Exception(f"Upload falhou: {resp.text}")

def publish_post(post, image_url):
    """Publica um post no Instagram via Meta Graph API."""
    # Passo 1: criar container de mídia
    print(f"  → Criando container de mídia...")
    r = requests.post(f"{API_BASE}/{INSTAGRAM_USER_ID}/media", params={
        "image_url": image_url,
        "caption": post["caption"],
        "access_token": ACCESS_TOKEN,
    })
    data = r.json()
    if "id" not in data:
        raise Exception(f"Erro ao criar container: {data}")
    container_id = data["id"]
    print(f"  → Container criado: {container_id}")

    # Aguarda processamento
    time.sleep(5)

    # Passo 2: verificar status
    for _ in range(10):
        r = requests.get(f"{API_BASE}/{container_id}", params={
            "fields": "status_code",
            "access_token": ACCESS_TOKEN,
        })
        status = r.json().get("status_code", "")
        if status == "FINISHED":
            break
        elif status == "ERROR":
            raise Exception("Container com erro de processamento")
        print(f"  → Aguardando processamento... ({status})")
        time.sleep(3)

    # Passo 3: publicar
    print(f"  → Publicando...")
    r = requests.post(f"{API_BASE}/{INSTAGRAM_USER_ID}/media_publish", params={
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN,
    })
    data = r.json()
    if "id" not in data:
        raise Exception(f"Erro ao publicar: {data}")
    return data["id"]

def test_connection():
    """Testa a conexão com a API."""
    r = requests.get(f"{API_BASE}/{INSTAGRAM_USER_ID}", params={
        "fields": "id,username,name",
        "access_token": ACCESS_TOKEN,
    })
    data = r.json()
    if "username" in data:
        print(f"✅ Conexão OK — Instagram: @{data['username']} ({data.get('name','')})")
    else:
        print(f"❌ Erro: {data}")

def get_post_datetime(post):
    dt_str = f"{post['date']} {post['hora']}"
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

def show_schedule():
    """Mostra o calendário completo."""
    now = datetime.now()
    print("\n📅 CALENDÁRIO WASFIT — JUNHO 2026\n")
    print(f"{'POST':<6} {'DATA':<14} {'HORA':<8} {'STATUS':<12} {'ARQUIVO'}")
    print("─" * 65)
    for p in POSTS:
        dt = get_post_datetime(p)
        if dt < now:
            status = "✅ passado"
        elif dt.date() == now.date():
            status = "🔴 HOJE"
        else:
            dias = (dt.date() - now.date()).days
            status = f"⏳ em {dias}d"
        print(f"#{p['num']:<5} {p['date']:<14} {p['hora']:<8} {status:<12} {p['image']}")
    print()

def supabase_get_status(num):
    """Consulta status do post no Supabase."""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return None
        r = requests.get(f"{SUPABASE_URL}/rest/v1/wasfit_posts?num=eq.{num}&select=status",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
        if r.status_code == 200 and r.json():
            return r.json()[0].get("status")
    except:
        pass
    return None

def supabase_mark_published(num, instagram_post_id):
    """Marca post como publicado no Supabase."""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return
        requests.patch(f"{SUPABASE_URL}/rest/v1/wasfit_posts?num=eq.{num}",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
                     "Content-Type": "application/json"},
            json={"status": "published", "instagram_post_id": instagram_post_id,
                  "published_at": datetime.now().isoformat()})
        print(f"  → Supabase atualizado: published")
    except:
        pass

def publish_today():
    """Publica o post agendado para hoje SE o horário agendado já chegou."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    posts_today = [p for p in POSTS if p["date"] == today]
    if not posts_today:
        print(f"ℹ️  Nenhum post agendado para hoje ({today}).")
        return
    for post in posts_today:
        scheduled_dt = get_post_datetime(post)

        # ── Verificar se horário chegou ──────────────────────────────
        if now < scheduled_dt:
            diff = scheduled_dt - now
            mins = int(diff.total_seconds() // 60)
            print(f"⏳ Post #{post['num']} agendado para {post['hora']} — faltam {mins} minutos.")
            continue

        # ── Verificar se já foi publicado no Supabase ────────────────
        status = supabase_get_status(post["num"])
        if status == "published":
            print(f"✅ Post #{post['num']} já publicado anteriormente. Pulando.")
            continue

        print(f"\n📸 Publicando Post #{post['num']} — {post['date']} {post['hora']}")
        img_path = POSTS_DIR / post["image"]
        if not img_path.exists():
            print(f"❌ Imagem não encontrada: {img_path}")
            continue
        print(f"  → Upload da imagem: {post['image']}")
        try:
            image_url = upload_image_simple(img_path)
            print(f"  → URL: {image_url}")
            post_id = publish_post(post, image_url)
            print(f"  ✅ Publicado com sucesso! ID: {post_id}")
            supabase_mark_published(post["num"], post_id)
        except Exception as e:
            print(f"  ❌ Erro: {e}")

def publish_all_pending():
    """Publica todos os posts pendentes (data <= hoje)."""
    now = datetime.now()
    pending = [p for p in POSTS if get_post_datetime(p) <= now]
    if not pending:
        print("ℹ️  Nenhum post pendente para publicar.")
        return
    print(f"\n📢 Publicando {len(pending)} post(s) pendente(s)...\n")
    for post in pending:
        img_path = POSTS_DIR / post["image"]
        if not img_path.exists():
            print(f"❌ #{post['num']} — imagem não encontrada: {img_path}")
            continue
        print(f"📸 Post #{post['num']} — {post['date']} {post['hora']}")
        try:
            image_url = upload_image_simple(img_path)
            post_id = publish_post(post, image_url)
            print(f"  ✅ Publicado! ID: {post_id}\n")
            time.sleep(2)
        except Exception as e:
            print(f"  ❌ Erro: {e}\n")

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test" in args:
        test_connection()
    elif "--publish" in args:
        publish_today()
    elif "--all" in args:
        publish_all_pending()
    else:
        show_schedule()
        print("Comandos disponíveis:")
        print("  python3 wasfit_publisher.py --test      # testa conexão")
        print("  python3 wasfit_publisher.py --publish   # publica post de hoje")
        print("  python3 wasfit_publisher.py --all       # publica todos pendentes")

