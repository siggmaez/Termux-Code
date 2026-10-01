#!/usr/bin/env python3
import os, json, re, time, difflib, shutil, subprocess, urllib.request, urllib.error, getpass
from pathlib import Path
from datetime import datetime
try:
    import readline
except ImportError:
    readline = None

VERSION = "4.3.1"
ROOT = Path.cwd().resolve()
STATE = ROOT / ".termuxcode"
HISTORY_FILE = STATE / "history.json"
MEMORY_FILE = STATE / "memory.json"
CHECKPOINTS = STATE / "checkpoints"
UNDO = STATE / "undo"
CONFIG_DIR = Path.home() / ".termux-code"
CONFIG_FILE = CONFIG_DIR / "config.json"

PROVIDERS = {
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "preferred": "gemini-3.8-flash",
        "kind": "gemini",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "preferred": "",
        "kind": "openai",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "preferred": "",
        "kind": "anthropic",
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "preferred": "openai/gpt-oss-20b",
        "kind": "openai",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "preferred": "openrouter/free",
        "kind": "openai",
    },
    "compatible": {
        "label": "Другое / Universal API",
        "base_url": "",
        "preferred": "",
        "kind": "openai",
    },
}

def load_key_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    default = {"keys": [], "active": None}
    if not CONFIG_FILE.exists():
        return default
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if data.get("gemini_api_key"):
            key = data["gemini_api_key"].strip()
            data = {"keys":[{"name":"Default","key":key,"provider":"gemini"}],"active":"Default"}
            save_key_config(data)
        if not isinstance(data.get("keys"), list):
            return default
        changed = False
        for item in data["keys"]:
            if "provider" not in item:
                item["provider"] = "gemini"
                changed = True
        if changed: save_key_config(data)
        return data
    except Exception:
        return default

def save_key_config(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try: os.chmod(CONFIG_FILE, 0o600)
    except Exception: pass

def provider_choice():
    ids=list(PROVIDERS)
    print("\nПровайдер:")
    for i,pid in enumerate(ids,1):
        print(f"  {i}. {PROVIDERS[pid]['label']}")
    try:
        return ids[int(input("> ").strip())-1]
    except Exception:
        print("❌ Неверный выбор.")
        return None

def add_api_key(config=None):
    if config is None: config=load_key_config()
    pid=provider_choice()
    if not pid: return None
    name=input("Название API: ").strip()
    if not name or any(x.get("name","").lower()==name.lower() for x in config["keys"]):
        print("❌ Пустое или уже занятое название."); return None
    key=getpass.getpass("API key (ввод скрыт): ").strip()
    if not key:
        print("❌ API key не введён."); return None
    item={"name":name,"key":key,"provider":pid}
    if pid=="compatible":
        print("\nUniversal API поддерживает OpenAI-compatible формат.")
        print("Нужен Base URL сервиса, обычно он заканчивается на /v1.")
        base=input("Base URL (например https://api.example.com/v1): ").strip().rstrip("/")
        if not base:
            print("❌ Base URL обязателен."); return None
        item["base_url"]=base
    preferred=input("Предпочитаемая модель [можно Enter для авто]: ").strip()
    if preferred: item["preferred_model"]=preferred
    config["keys"].append(item); config["active"]=name; save_key_config(config)
    print(f"✅ «{name}» ({PROVIDERS[pid]['label']}) сохранён.")
    return item

def get_active_profile():
    cfg=load_key_config()
    active=cfg.get("active")
    for x in cfg["keys"]:
        if x.get("name")==active: return x
    return cfg["keys"][0] if cfg["keys"] else None

def choose_api_key(config=None):
    if config is None: config=load_key_config()
    if not config["keys"]:
        print("╔════════════════════════════════╗")
        print("║   TERMUX CODE v4 — SETUP       ║")
        print("╚════════════════════════════════╝")
        return add_api_key(config)
    active=config.get("active")
    print("\nСохранённые API:")
    for i,item in enumerate(config["keys"],1):
        pid=item.get("provider","gemini")
        mark=" ← активный" if item.get("name")==active else ""
        print(f"  {i}. {item.get('name')} [{PROVIDERS.get(pid,{}).get('label',pid)}]{mark}")
    print("  N. Добавить новый API")
    c=input("Выбери API [Enter = активный]: ").strip()
    if not c and active:
        return get_active_profile()
    if c.lower()=="n": return add_api_key(config)
    try:
        item=config["keys"][int(c)-1]
        config["active"]=item["name"]; save_key_config(config)
        print(f"✅ Выбран «{item['name']}»."); return item
    except Exception:
        print("❌ Неверный выбор."); return choose_api_key(config)

def active_api_name():
    p=get_active_profile()
    return p.get("name","Unknown") if p else "None"

def api_key_menu():
    cfg=load_key_config()
    print("\nAPI Manager")
    print("1. Выбрать API\n2. Добавить API\n3. Удалить API\n4. Назад")
    c=input("> ").strip()
    if c=="1": choose_api_key(cfg)
    elif c=="2": add_api_key(cfg)
    elif c=="3":
        if not cfg["keys"]: print("Нет сохранённых API."); return
        for i,x in enumerate(cfg["keys"],1):
            print(f"{i}. {x['name']} [{PROVIDERS.get(x.get('provider','gemini'),{}).get('label')}]")
        try:
            idx=int(input("Какой удалить? ").strip())-1
            item=cfg["keys"][idx]
            if input(f"Удалить «{item['name']}»? [y/N]: ").lower() not in {"y","yes","д","да"}: return
            removed=cfg["keys"].pop(idx)
            if cfg.get("active")==removed["name"]:
                cfg["active"]=cfg["keys"][0]["name"] if cfg["keys"] else None
            save_key_config(cfg); print("✅ Удалено.")
        except Exception: print("❌ Неверный выбор.")

# Migrate/use existing Gemini environment key without storing it.
_env_key=os.environ.get("GEMINI_API_KEY","").strip()
if _env_key:
    ENV_PROFILE={"name":"environment","key":_env_key,"provider":"gemini"}
else:
    ENV_PROFILE=None
    if not load_key_config()["keys"]:
        choose_api_key()

MODELS = ["gemini-3.8-flash"]
MAX_RETRIES = 3
MAX_TOOL_STEPS = 8
MAX_READ = 50000
IGNORE = {".git", ".gradle", ".idea", "__pycache__", "node_modules", "build", "dist", ".venv", "venv", ".termuxcode"}

SYSTEM = """You are Termux Code v4.3.1, a coding agent in Android Termux.
Work only inside the current project. Be concise.
You receive a project tree and may request tools.

IMPORTANT: When requesting a tool, output ONLY one tool call and no prose.
Do not use provider-specific tool-call syntax.
Tool syntax (one tool call per response):
<tool name="read_file">{"path":"main.py"}</tool>
<tool name="list_files">{}</tool>
<tool name="search">{"query":"foo"}</tool>
<tool name="write_file">{"path":"main.py","content":"FULL FILE CONTENT"}</tool>
<tool name="run_python">{"path":"main.py"}</tool>

Use tools when needed. Read before editing existing files.
For write_file always send the FULL new file content.
Do not access paths outside the project.
Do not install packages or run arbitrary shell commands.
When the task is complete, answer normally without a tool call.
"""

def ensure_state():
    STATE.mkdir(exist_ok=True)
    CHECKPOINTS.mkdir(exist_ok=True)
    UNDO.mkdir(exist_ok=True)
    for p, default in [(HISTORY_FILE, []), (MEMORY_FILE, {})]:
        if not p.exists():
            p.write_text(json.dumps(default, indent=2), encoding="utf-8")

def safe(rel):
    try:
        p=(ROOT/rel).resolve()
        p.relative_to(ROOT)
        return p
    except Exception:
        return None

def files():
    out=[]
    for p in ROOT.rglob("*"):
        try:
            if p.is_file():
                r=p.relative_to(ROOT)
                if not any(x in IGNORE for x in r.parts):
                    out.append(str(r))
        except (PermissionError, OSError):
            continue
    return sorted(out)

def tree():
    fs=files()
    return "\n".join(f"- {x}" for x in fs[:500]) or "(empty project)"

def load_json(p, default):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return default

def save_json(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def history_add(role, text):
    h=load_json(HISTORY_FILE, [])
    h.append({"role":role,"text":text,"time":datetime.now().isoformat(timespec="seconds")})
    save_json(HISTORY_FILE, h[-100:])


def profile_base(profile):
    pid=profile.get("provider","gemini")
    return profile.get("base_url") or PROVIDERS.get(pid,{}).get("base_url","")

def request_json(url, method="GET", body=None, headers=None, timeout=45):
    data=json.dumps(body).encode() if body is not None else None
    h={"Accept":"application/json"}
    if headers: h.update(headers)
    if body is not None: h["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=data,headers=h,method=method)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=r.read().decode("utf-8",errors="replace")
        return json.loads(raw) if raw else {}

def discover_models(profile=None):
    profile=profile or ENV_PROFILE or get_active_profile()
    if not profile: return []
    pid=profile.get("provider","gemini"); key=profile.get("key","")
    try:
        if pid=="gemini":
            data=request_json(f"{profile_base(profile)}/models?pageSize=1000&key={key}")
            names=[]
            for m in data.get("models",[]):
                if "generateContent" not in m.get("supportedGenerationMethods",[]): continue
                n=m.get("name","").replace("models/","",1); low=n.lower()
                if n.startswith("gemini-") and not any(x in low for x in ("embedding","tts","image","veo","imagen","aqa")):
                    names.append(n)
        elif pid=="anthropic":
            data=request_json(f"{profile_base(profile)}/models?limit=100",
                headers={"x-api-key":key,"anthropic-version":"2023-06-01"})
            names=[x.get("id") for x in data.get("data",[]) if x.get("id")]
        else:
            data=request_json(f"{profile_base(profile)}/models",
                headers={"Authorization":f"Bearer {key}"})
            names=[x.get("id") for x in data.get("data",[]) if x.get("id")]
        preferred=profile.get("preferred_model") or PROVIDERS.get(pid,{}).get("preferred","")
        def score(n):
            l=n.lower(); s=10000 if n==preferred else 0
            if "flash" in l: s+=800
            if any(x in l for x in ("embed","whisper","tts","audio","image","guard","moderation")): s-=5000
            return s
        return sorted(dict.fromkeys(names),key=score,reverse=True)
    except urllib.error.HTTPError as e:
        try:
            detail=e.read().decode("utf-8",errors="replace")
        except Exception:
            detail=""
        print(f"⚠ {profile.get('name','API')}: /models → HTTP {e.code}")
        if detail:
            print("  " + detail[:700].replace("\n"," "))
        return []
    except Exception as e:
        print(f"⚠ {profile.get('name','API')}: не удалось получить модели: {e}")
        return []

def call_profile(profile, model, messages):
    pid=profile.get("provider","gemini"); key=profile.get("key",""); base=profile_base(profile)
    if not key: return None,"API key missing",0
    try:
        if pid=="gemini":
            body={"system_instruction":{"parts":[{"text":SYSTEM}]},
                  "contents":[{"role":"user","parts":[{"text":messages}]}],
                  "generationConfig":{"temperature":0.15}}
            data=request_json(f"{base}/models/{model}:generateContent?key={key}",
                              "POST",body,timeout=120)
            parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
            return "".join(x.get("text","") for x in parts),None,200
        if pid=="anthropic":
            body={"model":model,"max_tokens":8192,"temperature":0.15,
                  "system":SYSTEM,"messages":[{"role":"user","content":messages}]}
            data=request_json(f"{base}/messages","POST",body,
                {"x-api-key":key,"anthropic-version":"2023-06-01"},120)
            text="".join(x.get("text","") for x in data.get("content",[]) if x.get("type")=="text")
            return text,None,200
        body={"model":model,"temperature":0.15,
              "messages":[{"role":"system","content":SYSTEM},{"role":"user","content":messages}]}
        data=request_json(f"{base}/chat/completions","POST",body,
                          {"Authorization":f"Bearer {key}"},120)
        text=data.get("choices",[{}])[0].get("message",{}).get("content","")
        return text,None,200
    except urllib.error.HTTPError as e:
        detail=e.read().decode(errors="replace")
        return None,f"API {e.code}: {detail}",e.code
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return None,str(e),0

def all_profiles():
    out=[]
    if ENV_PROFILE: out.append(ENV_PROFILE)
    cfg=load_key_config()
    active=cfg.get("active")
    saved=list(cfg.get("keys",[]))
    saved.sort(key=lambda x: 0 if x.get("name")==active else 1)
    out.extend(saved)
    # Deduplicate by provider+key.
    seen=set(); result=[]
    for p in out:
        sig=(p.get("provider"),p.get("key"))
        if sig not in seen:
            seen.add(sig); result.append(p)
    return result

def smart_api(messages):
    profiles=all_profiles()
    if not profiles: return None,"No API configured"
    last_err="No usable model"
    for pi,profile in enumerate(profiles):
        pid=profile.get("provider","gemini")
        label=PROVIDERS.get(pid,{}).get("label",pid)
        models=discover_models(profile)
        if not models:
            explicit=profile.get("preferred_model") or PROVIDERS.get(pid,{}).get("preferred","")
            if explicit:
                print(f"  ℹ /models недоступен; пробую настроенную модель: {explicit}")
                models=[explicit]
            else:
                print(f"  ⚠ {profile.get('name')}: укажи модель в /apikey")
                continue
        # Limit fallback sweep to avoid hammering huge catalogs.
        for mi,model in enumerate(models[:8]):
            prefix="model" if pi==0 and mi==0 else "↪ fallback"
            print(f"  {prefix}: {label} / {profile.get('name')} / {model}")
            answer,err,code=call_profile(profile,model,messages)
            if answer: return answer,None
            last_err=err or last_err
            if code==429:
                print("  ⚠ 429: лимит; пробую другой API/провайдер")
                break
            if code in (503,502,504,404):
                print(f"  ⚠ {code}: пробую следующую модель")
                continue
            # Auth/billing/bad request: don't hammer other models on same profile.
            if code in (400,401,402,403):
                print(f"  ⚠ {code}: переключаю API/провайдер")
                break
            if code==0: break
    return None,last_err

TOOL_NAMES={"read_file","list_files","search","write_file","run_python"}

def _tool_json(name, raw):
    name=(name or "").strip()
    if name not in TOOL_NAMES: return None
    try:
        args=json.loads((raw or "").strip() or "{}")
        return (name,args) if isinstance(args,dict) else None
    except Exception:
        return None

def _xmlish_args(body):
    args={}
    for m in re.finditer(r'<arg_key>\\s*(.*?)\\s*</arg_key>\\s*<arg_value>(.*?)</arg_value>',body or "",re.S|re.I):
        key=m.group(1).strip()
        if key: args[key]=m.group(2)
    return args

def parse_tool(text):
    """Tolerant parser for common tool-call dialects emitted by routed LLMs."""
    text=text or ""
    patterns=[
        r'<tool\\s+name=["\\\']([^"\\\']+)["\\\']\\s*>\\s*(\\{.*?\\})\\s*</tool>',
        r'<tool_name\\s*=\\s*["\\\']([^"\\\']+)["\\\']\\s*>\\s*(\\{.*?\\})\\s*</tool_name>',
        r'<tool_call\\s*=\\s*["\\\']([^"\\\']+)["\\\']\\s*>\\s*(\\{.*?\\})\\s*</tool_call>',
        r'<invoke\\s*=\\s*["\\\']([^"\\\']+)["\\\']\\s*>\\s*(\\{.*?\\})\\s*(?:</tool>\\s*)?</invoke>',
        r'<function\\s+name=["\\\']([^"\\\']+)["\\\']\\s*>\\s*(\\{.*?\\})\\s*</function>',
    ]
    for pat in patterns:
        m=re.search(pat,text,re.S|re.I)
        if m:
            parsed=_tool_json(m.group(1),m.group(2))
            if parsed: return parsed

    # <tool_call>write_file<arg_key>path</arg_key><arg_value>...</arg_value>...</tool_call>
    m=re.search(r'<tool_call>\\s*([A-Za-z_]\\w*)\\s*(.*?)</tool_call>',text,re.S|re.I)
    if m and m.group(1) in TOOL_NAMES:
        args=_xmlish_args(m.group(2))
        if args or not m.group(2).strip(): return m.group(1),args

    # <|tool_call_start|>[read_file(path='x')]<|tool_call_end|>
    m=re.search(r'<\|tool_call_start\|>\s*\[\s*([A-Za-z_]\w*)\s*\((.*?)\)\s*\]\s*<\|tool_call_end\|>',text,re.S)
    if m and m.group(1) in TOOL_NAMES:
        args={}; body=m.group(2).strip()
        for am in re.finditer(r'([A-Za-z_]\\w*)\\s*=\\s*(["\\\'])(.*?)\\2',body,re.S): args[am.group(1)]=am.group(3)
        if body and not args: return ("invalid",{})
        return m.group(1),args

    # function({JSON}) / tool({JSON}) printed as text
    names="|".join(re.escape(x) for x in TOOL_NAMES)
    m=re.search(r'(?:^|[\\n`])\\s*('+names+r')\\s*\\(\\s*(\\{.*?\\})\\s*\\)',text,re.S)
    if m:
        parsed=_tool_json(m.group(1),m.group(2))
        if parsed: return parsed

    # Common JSON function-call envelopes printed as text.
    for pat in [
        r'\\{\\s*"name"\\s*:\\s*"([^"]+)"\\s*,\\s*"arguments"\\s*:\\s*(\\{.*?\\})\\s*\\}',
        r'\\{\\s*"function"\\s*:\\s*\\{\\s*"name"\\s*:\\s*"([^"]+)"\\s*,\\s*"arguments"\\s*:\\s*(\\{.*?\\})\\s*\\}\\s*\\}',
    ]:
        m=re.search(pat,text,re.S)
        if m:
            parsed=_tool_json(m.group(1),m.group(2))
            if parsed: return parsed
    return None

def read_file(path):
    p=safe(path)
    if not p or not p.is_file(): return "ERROR: file not found"
    try:
        if p.stat().st_size>MAX_READ: return "ERROR: file too large"
        return p.read_text(encoding="utf-8")
    except Exception as e: return f"ERROR: {e}"

def search(q):
    if not q: return "ERROR: empty query"
    hits=[]
    for f in files():
        txt=read_file(f)
        if txt.startswith("ERROR:"): continue
        for i,line in enumerate(txt.splitlines(),1):
            if q.lower() in line.lower():
                hits.append(f"{f}:{i}: {line[:240]}")
                if len(hits)>=80: return "\n".join(hits)
    return "\n".join(hits) or "No matches"

def snapshot_undo(path, old):
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    d=UNDO/stamp; d.mkdir()
    meta={"path":path,"existed":old is not None}
    save_json(d/"meta.json",meta)
    if old is not None: (d/"old.txt").write_text(old,encoding="utf-8")

def write_file(path, content):
    if isinstance(content,str) and "\\n" in content and "\n" not in content:
        content=content.replace("\\r\\n","\n").replace("\\n","\n").replace("\\t","\t")
    p=safe(path)
    if not p: return "ERROR: blocked path"
    old=p.read_text(encoding="utf-8") if p.exists() else None
    before=(old or "").splitlines(True); after=content.splitlines(True)
    diff="".join(difflib.unified_diff(before,after,fromfile=path+":old",tofile=path+":new"))
    print("\n--- DIFF ---")
    print(diff[:12000] or "(new/empty file)")
    ans=input("Apply this change? [y/N]: ").strip().lower()
    if ans not in {"y","yes","д","да"}: return "User rejected change"
    snapshot_undo(path,old)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(content,encoding="utf-8")
    return f"OK: wrote {path}"

def run_python(path):
    p=safe(path)
    if not p or not p.is_file() or p.suffix!=".py": return "ERROR: valid .py file required"
    try:
        r=subprocess.run(["python",str(p)],cwd=ROOT,text=True,capture_output=True,timeout=20)
        return f"exit={r.returncode}\nSTDOUT:\n{r.stdout[-6000:]}\nSTDERR:\n{r.stderr[-6000:]}"
    except subprocess.TimeoutExpired: return "ERROR: process timed out after 20s"
    except Exception as e: return f"ERROR: {e}"

def tool_exec(name,args):
    if name=="read_file": return read_file(args.get("path",""))
    if name=="list_files": return tree()
    if name=="search": return search(args.get("query",""))
    if name=="write_file": return write_file(args.get("path",""),args.get("content",""))
    if name=="run_python": return run_python(args.get("path",""))
    return "ERROR: unknown tool"

def agent(prompt):
    h=load_json(HISTORY_FILE,[])
    recent="\n".join(f"{x['role']}: {x['text'][:1500]}" for x in h[-8:])
    mem=load_json(MEMORY_FILE,{})
    convo=f"""PROJECT ROOT: {ROOT}
PROJECT TREE:
{tree()}

PROJECT MEMORY:
{json.dumps(mem,ensure_ascii=False)}

RECENT CHAT:
{recent}

USER:
{prompt}"""
    for step in range(MAX_TOOL_STEPS):
        print(f"◆ AI step {step+1}/{MAX_TOOL_STEPS}")
        answer, err = smart_api(convo)
        if not answer:
            print("❌",err); return
        call=parse_tool(answer)
        if not call:
            print(answer.strip())
            history_add("user",prompt); history_add("assistant",answer.strip())
            return
        name,args=call
        print(f"  tool: {name}")
        result=tool_exec(name,args)
        print("  result:", result[:300].replace("\n"," "))
        convo += f"\n\nASSISTANT TOOL REQUEST:\n{answer}\n\nTOOL RESULT:\n{result}\nContinue the task."
    print("⚠ Agent step limit reached.")

def checkpoint(name):
    name=re.sub(r"[^A-Za-z0-9._-]","_",name)[:60]
    if not name: print("Name required"); return
    d=CHECKPOINTS/name
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True)
    for f in files():
        src=ROOT/f; dst=d/f; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
    print(f"✓ checkpoint {name}")

def restore(name):
    d=CHECKPOINTS/name
    if not d.exists(): print("❌ checkpoint not found"); return
    if input("Restore checkpoint and overwrite project files? [y/N]: ").lower() not in {"y","yes","да","д"}: return
    for p in d.rglob("*"):
        if p.is_file():
            r=p.relative_to(d); dst=ROOT/r; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dst)
    print("✓ restored")

def undo():
    dirs=sorted([x for x in UNDO.iterdir() if x.is_dir()],reverse=True)
    if not dirs: print("Nothing to undo"); return
    d=dirs[0]; meta=load_json(d/"meta.json",{})
    p=safe(meta.get("path",""))
    if not p: return
    if meta.get("existed"):
        p.parent.mkdir(parents=True,exist_ok=True); p.write_text((d/"old.txt").read_text(encoding="utf-8"),encoding="utf-8")
    elif p.exists(): p.unlink()
    shutil.rmtree(d); print(f"✓ undone {meta.get('path')}")

def status():
    p=ENV_PROFILE or get_active_profile()
    pid=p.get("provider","gemini") if p else "none"
    print(f"""Termux Code v{VERSION}
Project: {ROOT}
Files: {len(files())}
Active API: {p.get("name","none") if p else "none"}
Provider: {PROVIDERS.get(pid,{}).get("label",pid)}
Fallback: models + saved APIs/providers
History: {len(load_json(HISTORY_FILE,[]))} messages
Checkpoints: {len(list(CHECKPOINTS.iterdir())) if CHECKPOINTS.exists() else 0}
""")

HELP="""Commands:
/files                    list project files
/read PATH                read a file
/search TEXT              search project
/run PATH.py              run Python file (20s timeout)
/fix PATH.py              run it and ask AI to fix errors
/refactor PATH            ask AI to refactor a file
/test PATH.py             ask AI to inspect/create tests
/undo                     undo last AI file write
/checkpoint NAME          save project checkpoint
/restore NAME             restore checkpoint
/history                  show recent history
/memory KEY=VALUE         save project note
/models                   show models for active provider
/status                   project status
/apikey                   manage providers and API keys
/clear                    clear chat history
/help                     show help
/exit                     quit

Anything else is sent to Agent Mode.
"""

def main():
    ensure_state()
    if readline:
        input_history = STATE / "input_history"
        try:
            if input_history.exists():
                readline.read_history_file(str(input_history))
            readline.set_history_length(300)
        except Exception:
            pass
    print("╔════════════════════════════════╗")
    print("║       TERMUX CODE v4.3.1         ║")
    print("║        Agent Edition           ║")
    print("╚════════════════════════════════╝")
    print(f"📂 {ROOT}\nType /help for commands.\n")
    while True:
        try: s=input("Termux Code > ").strip()
        except KeyboardInterrupt:
            print("\nДля выхода используй /exit"); continue
        except EOFError:
            print("\nBye!"); break
        if not s: continue
        if readline:
            try: readline.write_history_file(str(STATE / "input_history"))
            except Exception: pass
        if s in {"/exit","exit","quit"}: break
        if s=="/help": print(HELP); continue
        if s=="/files": print(tree()); continue
        if s.startswith("/read "): print(read_file(s[6:].strip())); continue
        if s.startswith("/search "): print(search(s[8:].strip())); continue
        if s.startswith("/run "): print(run_python(s[5:].strip())); continue
        if s.startswith("/fix "):
            f=s[5:].strip(); result=run_python(f); print(result)
            agent(f"Fix {f}. Here is its latest run result:\n{result}"); continue
        if s.startswith("/refactor "): agent(f"Refactor {s[10:].strip()} while preserving behavior. Read it first."); continue
        if s.startswith("/test "): agent(f"Inspect {s[6:].strip()}, create or improve appropriate Python tests, and run safe Python tests if useful."); continue
        if s=="/undo": undo(); continue
        if s.startswith("/checkpoint "): checkpoint(s[12:].strip()); continue
        if s.startswith("/restore "): restore(s[9:].strip()); continue
        if s=="/history":
            for x in load_json(HISTORY_FILE,[])[-20:]: print(f"{x['role']}> {x['text'][:500]}")
            continue
        if s.startswith("/memory "):
            pair=s[8:].strip()
            if "=" not in pair: print("Use /memory key=value"); continue
            k,v=pair.split("=",1); m=load_json(MEMORY_FILE,{}); m[k.strip()]=v.strip(); save_json(MEMORY_FILE,m); print("✓ saved"); continue
        if s=="/models":
            p=ENV_PROFILE or get_active_profile()
            if not p:
                print("❌ API не настроен."); continue
            pid=p.get("provider","gemini")
            print(f"\nМодели: {PROVIDERS.get(pid,{}).get('label',pid)} / {p.get('name')}")
            models=discover_models(p)
            if not models: print("  (модели не найдены)")
            else:
                preferred=p.get("preferred_model") or PROVIDERS.get(pid,{}).get("preferred","")
                for i,model in enumerate(models,1):
                    mark=" ★ preferred" if model==preferred else ""
                    print(f"  {i}. {model}{mark}")
            print(); continue
        if s=="/status": status(); continue
        if s=="/apikey": api_key_menu(); continue
        if s=="/clear": save_json(HISTORY_FILE,[]); print("✓ history cleared"); continue
        try:
            agent(s)
        except KeyboardInterrupt:
            print("\n⏹ Запрос отменён. Termux Code продолжает работу.")
            continue

if __name__=="__main__":
    main()
