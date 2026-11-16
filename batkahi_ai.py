import os, sqlite3, hashlib, hmac, secrets, re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import streamlit as st
import requests
import feedparser


CATEGORY_RULES = {
 "उत्तर प्रदेश": {
  "यूपी राजनीति": ["उत्तर प्रदेश","उत्तरप्रदेश","यूपी","लखनऊ","योगी","केशव मौर्य","अखिलेश","यूपी सरकार"],
  "यूपी प्रशासन": ["जिलाधिकारी","डीएम","एसडीएम","तहसील","नगर निगम","आईएएस","आईपीएस","प्रशासन"],
  "यूपी अपराध": ["यूपी पुलिस","हत्या","लूट","गिरफ्तार","एनकाउंटर","अपहरण"],
  "यूपी शिक्षा": ["यूपी बोर्ड","यूपीपीएससी","शिक्षक भर्ती","स्कूल","विश्वविद्यालय","कॉलेज"],
  "यूपी शहर/जिला": ["रायबरेली","अयोध्या","वाराणसी","प्रयागराज","कानपुर","गोरखपुर","आगरा","नोएडा","गाजियाबाद","मेरठ","मथुरा","झांसी","बरेली","सुल्तानपुर","सीतापुर","बाराबंकी","चित्रकूट","लखीमपुर","मुरादाबाद","अलीगढ़","आजमगढ़","बलिया","बस्ती","देवरिया","मिर्जापुर"]
 },
 "राष्ट्रीय": {"राष्ट्रीय राजनीति": ["लोकसभा","राज्यसभा","संसद","प्रधानमंत्री","पीएम मोदी","राहुल गांधी","भाजपा","कांग्रेस","चुनाव आयोग","केंद्र सरकार","सुप्रीम कोर्ट"]},
 "अंतरराष्ट्रीय": {"युद्ध/सुरक्षा": ["ईरान","इजरायल","इज़रायल","अमेरिका","ट्रंप","नेतन्याहू","मिसाइल","ड्रोन","युद्ध","गाजा","यूक्रेन","रूस"],
                  "विश्व राजनीति": ["संयुक्त राष्ट्र","नाटो","पाकिस्तान","चीन","ब्रिटेन","सऊदी","जॉर्डन"]},
 "क्रिकेट": {"भारतीय/अंतरराष्ट्रीय क्रिकेट": ["विराट कोहली","रोहित शर्मा","शुभमन गिल","सूर्यकुमार","संजू सैमसन","आईपीएल","बीसीसीआई","टेस्ट","वनडे","टी20","t20","क्रिकेट","बल्लेबाज","गेंदबाज"]},
 "खेल": {"अन्य खेल": ["फुटबॉल","हॉकी","टेनिस","बैडमिंटन","ओलंपिक","कुश्ती","कबड्डी","खिलाड़ी"]},
 "मनोरंजन": {"फिल्म/टीवी": ["बॉलीवुड","फिल्म","सिनेमा","अभिनेता","अभिनेत्री","एक्टर","एक्ट्रेस","वेब सीरीज","ओटीटी"]},
 "बिजनेस": {"व्यापार/बाजार": ["शेयर बाजार","सेंसेक्स","निफ्टी","रुपया","महंगाई","बजट","जीएसटी","कारोबार","बैंक","आरबीआई"]},
 "शिक्षा": {"परीक्षा/भर्ती": ["परीक्षा","रिजल्ट","एडमिट कार्ड","भर्ती","यूजीसी","नीट","जेईई","सीयूईटी","विश्वविद्यालय"]},
 "टेक्नोलॉजी": {"टेक/AI": ["एआई","आर्टिफिशियल इंटेलिजेंस"," ai ","टेक्नोलॉजी","स्मार्टफोन","मोबाइल","गूगल","एप्पल","माइक्रोसॉफ्ट","साइबर"]},
 "अपराध": {"क्राइम/पुलिस": ["हत्या","चोरी","लूट","गिरफ्तार","पुलिस","आरोपी","अपराध","दुष्कर्म","फायरिंग"]},
 "धर्म": {"धर्म/आस्था": ["मंदिर","मस्जिद","धर्म","राम","कृष्ण","काशी","तीर्थ","पूजा","संत","महाकुंभ"]},
 "स्वास्थ्य": {"हेल्थ/मेडिकल": ["स्वास्थ्य","अस्पताल","डॉक्टर","मरीज","बीमारी","वायरस","दवा","मेडिकल","टीका"]},
 "वायरल": {"वायरल/ट्रेंडिंग": ["वायरल","सोशल मीडिया","वीडियो वायरल","ट्रेंडिंग"]},
 "ऑटोमोबाइल": {"कार/बाइक": ["कार","बाइक","ऑटोमोबाइल","इलेक्ट्रिक वाहन","ईवी","एसयूवी"]}
}
CATEGORY_NAMES = list(CATEGORY_RULES) + ["अन्य"]

def classify_story(title, summary=""):
    text = f"{title or ''} {summary or ''}".casefold()
    found = []
    for category, subcats in CATEGORY_RULES.items():
        for subcategory, words in subcats.items():
            if any(word.casefold() in text for word in words):
                found.append((category, subcategory))
                break
    return found[:3] or [("अन्य", "अन्य")]

def ensure_category_columns():
    with db() as con:
        if DATABASE_URL:
            cols = {r["column_name"] for r in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='news_stories'").fetchall()}
        else:
            cols = {r["name"] for r in con.execute("PRAGMA table_info(news_stories)")}
        for name in ("category", "subcategory", "categories"):
            if name not in cols:
                con.execute(f"ALTER TABLE news_stories ADD COLUMN {name} TEXT DEFAULT ''")
        rows = con.execute("SELECT id,title,summary FROM news_stories WHERE category IS NULL OR category=''").fetchall()
        for row in rows:
            pairs = classify_story(row["title"], row["summary"])
            con.execute("UPDATE news_stories SET category=?,subcategory=?,categories=? WHERE id=?",
                (pairs[0][0], pairs[0][1], " | ".join(f"{c}/{s}" for c,s in pairs), row["id"]))


APP_DIR = Path(__file__).parent
DB_PATH = Path(os.getenv("BATKAHI_DB_PATH", str(APP_DIR / "data" / "batkahi_ai.db")))
LANG = "en"

TEXT = {
 "hi": {
  "title":"BATKAHI AI", "sub":"मीडिया इंटेलिजेंस एवं ग्रोथ प्लेटफॉर्म",
  "dashboard":"डैशबोर्ड", "channels":"चैनल प्रबंधन", "news":"न्यूज़ रडार",
  "settings":"सेटिंग्स", "logout":"लॉग आउट", "welcome":"स्वागत है",
  "total_channels":"कुल चैनल", "youtube":"YouTube चैनल", "stories":"न्यूज़ स्टोरीज़",
  "add_channel":"नया चैनल जोड़ें", "name":"चैनल का नाम", "platform":"प्लेटफॉर्म",
  "channel_id":"चैनल ID / Page ID", "save":"सेव करें", "saved":"सेव हो गया",
  "feeds":"RSS फीड URL (हर लाइन में एक)", "refresh":"न्यूज़ अपडेट करें",
  "headline":"हेडलाइन", "source":"सोर्स", "published":"प्रकाशित",
  "login":"एडमिन लॉगिन", "password":"पासवर्ड", "sign_in":"लॉगिन करें",
  "wrong":"गलत पासवर्ड", "api":"YouTube API Key", "api_help":"यह key केवल public channel/video data पढ़ने के लिए है।",
  "test":"YouTube चैनल डेटा जांचें", "not_configured":"API key उपलब्ध नहीं है। Settings में जोड़ें।",
  "no_news":"अभी कोई स्टोरी नहीं। RSS फीड जोड़कर अपडेट करें।",
  "delete":"हटाएं", "confirm":"हटाने की पुष्टि", "local":"डेटा इसी कंप्यूटर पर SQLite में सेव होता है।",
  "note":"खबरों की कैटेगरी headline और summary के आधार पर अपने आप तय होती है।",
  "all_websites":"सभी वेबसाइटें", "website_filter":"वेबसाइट चुनें",
  "sort_time":"समय के अनुसार क्रम", "latest_first":"नवीनतम पहले", "oldest_first":"सबसे पुरानी पहले",
  "showing":"दिखाई जा रही खबरें"
 },
 "en": {
  "title":"BATKAHI AI", "sub":"Media Intelligence & Growth Platform",
  "dashboard":"Dashboard", "channels":"Channel Manager", "news":"News Radar",
  "settings":"Settings", "logout":"Log out", "welcome":"Welcome",
  "total_channels":"Total channels", "youtube":"YouTube channels", "stories":"News stories",
  "add_channel":"Add channel", "name":"Channel name", "platform":"Platform",
  "channel_id":"Channel ID / Page ID", "save":"Save", "saved":"Saved",
  "feeds":"RSS feed URLs (one per line)", "refresh":"Refresh news",
  "headline":"Headline", "source":"Source", "published":"Published",
  "login":"Admin login", "password":"Password", "sign_in":"Sign in",
  "wrong":"Incorrect password", "api":"YouTube API Key", "api_help":"Used only for public channel/video data.",
  "test":"Test YouTube channel data", "not_configured":"API key not set. Add it in Settings.",
  "no_news":"No stories yet. Add RSS feeds and refresh.",
  "delete":"Delete", "confirm":"Confirm deletion", "local":"Data is stored locally in SQLite on this computer.",
  "note":"Stories are automatically categorized using headline and summary keyword rules.",
  "all_websites":"All websites", "website_filter":"Select website",
  "sort_time":"Sort by time", "latest_first":"Latest first", "oldest_first":"Oldest first",
  "showing":"Showing stories"
 }
}

# Streamlit Community Cloud secrets are supported; environment variables remain supported for other hosts.
try:
    _streamlit_db_url = st.secrets.get("DATABASE_URL", "")
    _streamlit_admin_username = st.secrets.get("BATKAHI_ADMIN_USERNAME", "admin")
    _streamlit_admin_password = st.secrets.get("BATKAHI_ADMIN_PASSWORD", "")
except Exception:
    _streamlit_db_url = ""
    _streamlit_admin_username = "admin"
    _streamlit_admin_password = ""
DATABASE_URL = (os.getenv("DATABASE_URL", "") or _streamlit_db_url).strip()

class DBResult:
    def __init__(self, cursor):
        self.cursor = cursor
        self.rowcount = cursor.rowcount
    def fetchone(self):
        return self.cursor.fetchone()
    def fetchall(self):
        return self.cursor.fetchall()

class DBConnection:
    """Use SQLite locally and PostgreSQL for the shared online database."""
    def __init__(self, connection, is_postgres=False):
        self.connection = connection
        self.is_postgres = is_postgres
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return self.connection.__exit__(exc_type, exc, tb)
    def execute(self, sql, params=()):
        if self.is_postgres:
            sql = sql.strip()
            match = re.match(r"INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)", sql, re.I)
            if match:
                table = match.group(1).lower()
                conflict_key = "url" if table == "news_stories" else "key"
                sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, count=1, flags=re.I)
                sql = sql.rstrip().rstrip(";") + f" ON CONFLICT ({conflict_key}) DO NOTHING"
            sql = sql.replace("?", "%s")
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            return DBResult(cursor)
        return self.connection.execute(sql, params)
    def executescript(self, script):
        if self.is_postgres:
            cursor = self.connection.cursor()
            for statement in script.split(";"):
                if statement.strip():
                    cursor.execute(statement)
            return DBResult(cursor)
        return self.connection.executescript(script)

def db():
    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row
        return DBConnection(psycopg.connect(DATABASE_URL, row_factory=dict_row), True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return DBConnection(con, False)

def init_db():
    if not DATABASE_URL:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as con:
        if DATABASE_URL:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS channels(
              id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, platform TEXT NOT NULL,
              channel_id TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS news_stories(
              id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, url TEXT UNIQUE, source TEXT,
              published TEXT, summary TEXT, fetched_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS api_logs(
              id BIGSERIAL PRIMARY KEY, service TEXT, status TEXT, detail TEXT, created_at TEXT NOT NULL
            );
            """)
        else:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS channels(
              id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, platform TEXT NOT NULL,
              channel_id TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS news_stories(
              id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, url TEXT UNIQUE,
              source TEXT, published TEXT, summary TEXT, fetched_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS api_logs(
              id INTEGER PRIMARY KEY AUTOINCREMENT, service TEXT, status TEXT,
              detail TEXT, created_at TEXT NOT NULL
            );
            """)
        initial_password = os.getenv("BATKAHI_ADMIN_PASSWORD", "") or _streamlit_admin_password or "CHANGE-ME-IMMEDIATELY"
        initial_username = os.getenv("BATKAHI_ADMIN_USERNAME", "") or _streamlit_admin_username or "admin"
        defaults = {
          "admin_username": initial_username,
          "admin_password_hash": hashlib.sha256(initial_password.encode()).hexdigest(),
          "rss_feeds": "https://www.thehindu.com/news/national/feeder/default.rss\nhttps://indianexpress.com/section/india/feed/",
          "youtube_api_key": ""
        }
        for k,v in defaults.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))

def setting(key, default=""):
    with db() as con:
        row=con.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
    return row["value"] if row else default

def set_setting(key, value):
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,value))

def t(key):
    return TEXT[st.session_state.get("lang","hi")][key]

def logged_in():
    return st.session_state.get("authenticated", False)

def story_timestamp(item):
    """Convert RSS publication time to a sortable timestamp; fall back to fetch time."""
    value = item["published"] or ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        pass
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError, OverflowError):
        pass
    try:
        dt = datetime.fromisoformat((item["fetched_at"] or "").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0

init_db()
ensure_category_columns()
st.set_page_config(page_title="BATKAHI AI", page_icon="📰", layout="wide")

if "lang" not in st.session_state:
    st.session_state.lang = "hi"

# Login screen
if not logged_in():
    a,b,c = st.columns([1,1.3,1])
    with b:
        st.markdown("<h1 style='text-align:center'>📰 BATKAHI AI</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center'>{t('sub')}</p>", unsafe_allow_html=True)
        st.session_state.lang = st.selectbox("Language / भाषा", ["hi","en"], format_func=lambda x: "हिन्दी" if x=="hi" else "English")
        st.subheader(t("login"))
        login_id=st.text_input("Login ID")
        pwd=st.text_input(t("password"), type="password")
        if st.button(t("sign_in"), use_container_width=True):
            hashed=hashlib.sha256(pwd.encode()).hexdigest()
            if hmac.compare_digest(login_id.strip(), setting("admin_username", "admin")) and hmac.compare_digest(hashed, setting("admin_password_hash")):
                st.session_state.authenticated=True
                st.rerun()
            else:
                st.error(t("wrong"))
        st.caption("Login ID और Password वही डालें जो Streamlit Secrets में सेट किए हैं।")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("# 📰 BATKAHI AI")
    st.caption(t("sub"))
    st.session_state.lang = st.selectbox("Language / भाषा", ["hi","en"], index=0 if st.session_state.lang=="hi" else 1,
                                         format_func=lambda x: "हिन्दी" if x=="hi" else "English")
    page=st.radio("Navigation", ["🏠 Home", "🗂️ Categories", t("news"), t("channels"), t("settings")])
    if st.button(t("logout"), use_container_width=True):
        st.session_state.authenticated=False
        st.rerun()

st.title("📰 " + t("title"))
st.caption(t("sub"))

if page == "🏠 Home":
    with db() as con:
        channels=con.execute("SELECT * FROM channels ORDER BY name").fetchall()
        stories=con.execute("SELECT COUNT(*) n FROM news_stories").fetchone()["n"]
        recent=con.execute("SELECT * FROM news_stories ORDER BY id DESC LIMIT 8").fetchall()
        category_counts=con.execute("SELECT category,COUNT(*) n FROM news_stories GROUP BY category ORDER BY n DESC").fetchall()
    youtube_count=sum(1 for x in channels if x["platform"]=="YouTube")
    c1,c2,c3=st.columns(3)
    c1.metric(t("total_channels"),len(channels))
    c2.metric(t("youtube"),youtube_count)
    c3.metric(t("stories"),stories)
    st.subheader("न्यूज़ होम")
    st.caption("सभी वेबसाइटों से आई खबरें एक ही जगह — विषय और क्षेत्र के अनुसार व्यवस्थित।")
    if category_counts:
        st.subheader("कैटेगरी ओवरव्यू")
        cols=st.columns(4)
        for i, row in enumerate(category_counts[:8]):
            cols[i % 4].metric(row["category"] or "अन्य", row["n"])
    st.subheader("ताज़ा खबरें")
    for item in recent:
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.caption(f"{item['category'] or 'अन्य'} / {item['subcategory'] or 'अन्य'} · {item['source'] or 'RSS'}")
            st.markdown(f"[खबर खोलें]({item['url']})")
    st.info(t("local"))
    st.subheader("Connected channels / जुड़े चैनल")
    if channels:
        st.dataframe([dict(Name=x["name"],Platform=x["platform"],ID=x["channel_id"] or "—") for x in channels],use_container_width=True,hide_index=True)
    else:
        st.caption("Channel list is empty. Add your network channels from Channel Manager.")

elif page == "🗂️ Categories":
    st.subheader("सभी न्यूज़ कैटेगरी")
    with db() as con:
        counts={r["category"]:r["n"] for r in con.execute("SELECT category,COUNT(*) n FROM news_stories GROUP BY category")}
        subs=con.execute("SELECT category,subcategory,COUNT(*) n FROM news_stories GROUP BY category,subcategory ORDER BY category,n DESC").fetchall()
    for category in CATEGORY_NAMES:
        with st.expander(f"{category} · {counts.get(category,0)} खबरें"):
            matches=[r for r in subs if r["category"]==category]
            if matches:
                for r in matches: st.write(f"• {r['subcategory']} — {r['n']}")
            else: st.caption("अभी कोई खबर नहीं।")
    st.caption("यह शुरुआती keyword-based automatic classification है। बेहतर सटीकता के लिए आगे AI classifier जोड़ा जा सकता है।")

elif page == t("channels"):
    st.subheader(t("channels"))
    with st.form("add_channel", clear_on_submit=True):
        name=st.text_input(t("name"))
        platform=st.selectbox(t("platform"),["YouTube","Facebook","Instagram","Other"])
        channel_id=st.text_input(t("channel_id"))
        submitted=st.form_submit_button(t("add_channel"))
        if submitted:
            if not name.strip():
                st.error("Channel name is required.")
            else:
                with db() as con:
                    con.execute("INSERT INTO channels(name,platform,channel_id,created_at) VALUES(?,?,?,?)",
                                (name.strip(),platform,channel_id.strip(),datetime.now().isoformat(timespec="seconds")))
                st.success(t("saved")); st.rerun()
    with db() as con:
        rows=con.execute("SELECT * FROM channels ORDER BY id DESC").fetchall()
    for r in rows:
        x,y=st.columns([5,1])
        x.write(f"**{r['name']}** · {r['platform']} · `{r['channel_id'] or 'No ID'}`")
        if y.button(t("delete"),key=f"del_{r['id']}"):
            st.session_state[f"confirm_{r['id']}"]=True
        if st.session_state.get(f"confirm_{r['id']}"):
            if st.button(t("confirm"),key=f"yes_{r['id']}"):
                with db() as con: con.execute("DELETE FROM channels WHERE id=?",(r["id"],))
                st.session_state.pop(f"confirm_{r['id']}",None); st.rerun()

elif page == t("news"):
    st.subheader(t("news"))
    feeds=st.text_area(t("feeds"),value=setting("rss_feeds"),height=120)
    if st.button(t("refresh")):
        set_setting("rss_feeds",feeds)
        total=0
        with st.spinner("Fetching RSS feeds..."):
            for feed_url in [x.strip() for x in feeds.splitlines() if x.strip()]:
                try:
                    parsed=feedparser.parse(feed_url)
                    for entry in parsed.entries[:30]:
                        title=entry.get("title","").strip()
                        link=entry.get("link","").strip()
                        if not title or not link: continue
                        source=parsed.feed.get("title",feed_url)
                        published=entry.get("published",entry.get("updated",""))
                        summary=entry.get("summary","")
                        pairs=classify_story(title,summary)
                        with db() as con:
                            cur=con.execute("""INSERT OR IGNORE INTO news_stories
                              (title,url,source,published,summary,fetched_at,category,subcategory,categories)
                              VALUES(?,?,?,?,?,?,?,?,?)""",
                              (title,link,source,published,summary,datetime.now().isoformat(timespec="seconds"),
                               pairs[0][0],pairs[0][1]," | ".join(f"{c}/{s}" for c,s in pairs)))
                            total += cur.rowcount
                except Exception as e:
                    with db() as con:
                        con.execute("INSERT INTO api_logs(service,status,detail,created_at) VALUES(?,?,?,?)",
                                    ("RSS","ERROR",str(e),datetime.now().isoformat(timespec="seconds")))
        st.success(f"Added {total} new stories.")

    with db() as con:
        items=con.execute("SELECT * FROM news_stories ORDER BY id DESC LIMIT 500").fetchall()

    # Cross-website filters: category, subcategory, website, date and keyword.
    sources=sorted({(x["source"] or "RSS") for x in items},key=str.casefold)
    cats=sorted({part.split("/",1)[0] for x in items
                 for part in (x["categories"] or f"{x['category']}/{x['subcategory']}").split(" | ") if part})
    f1,f2,f3,f4=st.columns(4)
    with f1: selected_category=st.selectbox("कैटेगरी",["सभी कैटेगरी"]+cats,key="filter_category")
    subs=sorted({part.split("/",1)[1] for x in items
                 for part in (x["categories"] or f"{x['category']}/{x['subcategory']}").split(" | ")
                 if part and (selected_category=="सभी कैटेगरी" or part.split("/",1)[0]==selected_category)})
    with f2: selected_subcategory=st.selectbox("सब-कैटेगरी",["सभी सब-कैटेगरी"]+subs,key="filter_subcategory")
    with f3: selected_source=st.selectbox(t("website_filter"),[t("all_websites")]+sources,key="news_website_filter")
    with f4: date_filter=st.selectbox("तारीख",["सभी तारीखें","आज","पिछले 7 दिन","पिछले 30 दिन"],key="news_date_filter")
    a,b=st.columns(2)
    with a: sort_choice=st.selectbox("Sort / क्रम",["Newest first","Oldest first","Headline A–Z","Website A–Z"],key="news_time_sort")
    with b: keyword=st.text_input("खबर खोजें",placeholder="हेडलाइन या खबर में शब्द…")
    if selected_category!="सभी कैटेगरी":
        items=[x for x in items if any(part.split("/",1)[0]==selected_category
               for part in (x["categories"] or f"{x['category']}/{x['subcategory']}").split(" | ") if part)]
    if selected_subcategory!="सभी सब-कैटेगरी":
        items=[x for x in items if any(part.split("/",1)[1]==selected_subcategory
               for part in (x["categories"] or f"{x['category']}/{x['subcategory']}").split(" | ") if "/" in part)]
    if selected_source!=t("all_websites"): items=[x for x in items if (x["source"] or "RSS")==selected_source]
    if keyword.strip():
        q=keyword.casefold().strip()
        items=[x for x in items if q in (x["title"] or "").casefold() or q in (x["summary"] or "").casefold()]
    if date_filter!="सभी तारीखें":
        now=datetime.now().astimezone()
        if date_filter=="आज":
            cutoff=now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
        else:
            cutoff=now.timestamp()-(7 if date_filter=="पिछले 7 दिन" else 30)*86400
        items=[x for x in items if story_timestamp(x)>=cutoff]
    if sort_choice=="Newest first": items=sorted(items,key=story_timestamp,reverse=True)
    elif sort_choice=="Oldest first": items=sorted(items,key=story_timestamp)
    elif sort_choice=="Headline A–Z": items=sorted(items,key=lambda x:(x["title"] or "").casefold())
    else: items=sorted(items,key=lambda x:(x["source"] or "").casefold())

    st.caption(f"{t('showing')}: {len(items)}")
    if not items:
        st.info(t("no_news"))
    for item in items:
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.caption(f"{item['category'] or 'अन्य'} / {item['subcategory'] or 'अन्य'} · {item['source'] or 'RSS'} · {item['published'] or item['fetched_at']}")
            if item["summary"]:
                st.write(item["summary"][:500].replace("<","&lt;"))
            st.markdown(f"[Open story]({item['url']})")

elif page == t("settings"):
    st.subheader(t("settings"))
    st.caption(t("local"))
    current=st.text_input(t("api"),value=setting("youtube_api_key"),type="password")
    st.caption(t("api_help"))
    if st.button("Save API settings"):
        set_setting("youtube_api_key",current.strip())
        st.success(t("saved"))
    st.divider()
    st.subheader("Change shared login / साझा लॉगिन बदलें")
    old=st.text_input("Current password",type="password")
    new_id=st.text_input("New Login ID", value=setting("admin_username", "admin"))
    new=st.text_input("New password (minimum 10 characters)",type="password")
    if st.button("Update shared login"):
        if hashlib.sha256(old.encode()).hexdigest()!=setting("admin_password_hash"):
            st.error("Current password is incorrect.")
        elif not new_id.strip():
            st.error("Login ID cannot be empty.")
        elif len(new)<10:
            st.error("Use at least 10 characters.")
        else:
            set_setting("admin_username",new_id.strip())
            set_setting("admin_password_hash",hashlib.sha256(new.encode()).hexdigest())
            st.success("Shared Login ID and password updated. All users will use the new login.")
    st.divider()
    st.subheader("YouTube API connection test")
    if st.button(t("test")):
        key=setting("youtube_api_key")
        if not key:
            st.warning(t("not_configured"))
        else:
            try:
                response=requests.get("https://www.googleapis.com/youtube/v3/channels",
                    params={"part":"snippet,statistics","id":"UC5vTj-l_FWQQkOjTpOwutnw","key":key},timeout=15)
                response.raise_for_status()
                data=response.json().get("items",[])
                if data:
                    item=data[0]
                    st.success("API connected")
                    st.write(item["snippet"]["title"])
                    st.json(item.get("statistics",{}))
                else:
                    st.warning("No channel data returned. Check channel ID and API key.")
            except Exception as e:
                st.error(f"API request failed: {e}")
