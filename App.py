import streamlit as st
import pandas as pd
from collections import defaultdict
import os

# Configurazione pagina
st.set_page_config(page_title="Ricerca Percorsi Adattatori", layout="wide")

# ---------------------------------------------------------------------------
# TITOLO
# ---------------------------------------------------------------------------
st.title("🔧 Ricerca Adattatori Aste Perforatrici Teleguidate")
st.markdown("---")

# ---------------------------------------------------------------------------
# CARICAMENTO DATI
# ---------------------------------------------------------------------------

@st.cache_data
def carica_dati(file_path=None, uploaded_file=None):
    """Carica i dati da file locale o da upload"""
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    elif file_path is not None and os.path.exists(file_path):
        df = pd.read_excel(file_path)
    else:
        return None, None
    
    # Pulizia nomi adattatori
    df["Attacco_1"] = df["ATTACCO_1"].str.replace(r"\s*\(.*?\)", "", regex=True)
    df["Attacco_2"] = df["ATTACCO_2"].str.replace(r"\s*\(.*?\)", "", regex=True)
    
    # Costruzione anagrafica_attacchi
    attacchi_1 = df[["ATTACCO_1", "Filetto_1", "Genere_1"]].rename(
        columns={"ATTACCO_1": "ATTACCO", "Filetto_1": "FILETTO", "Genere_1": "GENERE"}
    )
    
    attacchi_2 = df[["ATTACCO_2", "Filetto_2", "Genere_2"]].rename(
        columns={"ATTACCO_2": "ATTACCO", "Filetto_2": "FILETTO", "Genere_2": "GENERE"}
    )
    
    anagrafica_attacchi = (
        pd.concat([attacchi_1, attacchi_2], ignore_index=True)
          .drop_duplicates()
          .sort_values(by=["ATTACCO", "GENERE"])
          .reset_index(drop=True)
    )
    
    return df, anagrafica_attacchi

# Tentativo di caricare il file predefinito
FILE_EXCEL = "DW_lista_adattatori_completa.xlsx"
df, anagrafica_attacchi = carica_dati(file_path=FILE_EXCEL)

# Se il file predefinito non esiste, mostra l'uploader
if df is None:
    st.info("📁 Il file predefinito non è disponibile. Carica il tuo file Excel:")
    uploaded_file = st.file_uploader(
        "Carica il file Excel con gli adattatori",
        type=['xlsx', 'xls'],
        help="Il file deve contenere: Cd_Ar, ATTACCO_1, ATTACCO_2, Filetto_1, Filetto_2, Genere_1, Genere_2"
    )
    
    if uploaded_file is None:
        st.stop()
    
    df, anagrafica_attacchi = carica_dati(uploaded_file=uploaded_file)
    st.success(f"✅ File caricato: {len(df)} adattatori trovati")
else:
    st.success(f"✅ Database caricato: {len(df)} adattatori disponibili")
    
    # Opzione per caricare un file diverso
    with st.expander("🔄 Vuoi caricare un file diverso?"):
        uploaded_file = st.file_uploader(
            "Carica un altro file Excel",
            type=['xlsx', 'xls'],
            help="Il file deve contenere: Cd_Ar, ATTACCO_1, ATTACCO_2, Filetto_1, Filetto_2, Genere_1, Genere_2"
        )
        
        if uploaded_file is not None:
            df, anagrafica_attacchi = carica_dati(uploaded_file=uploaded_file)
            st.success(f"✅ Nuovo file caricato: {len(df)} adattatori trovati")
            st.rerun()

# ---------------------------------------------------------------------------
# FUNZIONI
# ---------------------------------------------------------------------------
def scambia_genere(genere):
    if genere == "M":
        return "F"
    elif genere == "F":
        return "M"
    else:
        return genere

def ricerca_attacco(attacco_input, anagrafica_attacchi):
    riga = anagrafica_attacchi[anagrafica_attacchi["ATTACCO"] == attacco_input].iloc[0]
    filetto = riga["FILETTO"]
    genere = riga["GENERE"]
    return (filetto, genere)

def costruisci_grafo(df):
    grafo = defaultdict(list)
    for _, row in df.iterrows():
        f1, g1 = row['Filetto_1'], row['Genere_1']
        f2, g2 = row['Filetto_2'], row['Genere_2']
        cd_ar = row['Cd_Ar']
        
        grafo[(f1, g1)].append(((f2, g2), cd_ar))
        grafo[(f2, g2)].append(((f1, g1), cd_ar))
    
    return grafo

def trova_percorsi(nodo_corrente, nodo_arrivo, articoli_usati, percorsi_trovati, max_articoli, grafo):
    if nodo_corrente == (nodo_arrivo[0], scambia_genere(nodo_arrivo[1])) and len(articoli_usati) > 0:
        percorsi_trovati.append(list(articoli_usati))
        return
    
    if len(articoli_usati) >= max_articoli:
        return
    
    for vicino, cd_ar in grafo[nodo_corrente]:
        if cd_ar in articoli_usati:
            continue
        
        nuovo_nodo_corrente = (vicino[0], scambia_genere(vicino[1]))
        articoli_usati.append(cd_ar)
        trova_percorsi(nuovo_nodo_corrente, nodo_arrivo, articoli_usati, percorsi_trovati, max_articoli, grafo)
        articoli_usati.pop()

def stampa_sequenza_attacchi(sequenza_articoli, df, attacco_partenza):
    sequenza = []
    nodo_necessario = attacco_partenza
    
    for cd_ar in sequenza_articoli:
        riga = df[df["Cd_Ar"] == cd_ar]

        if riga.empty:
            return f"❌ ERRORE: Codice articolo {cd_ar} non trovato nel dataset"
        riga = riga_df.iloc[0]
        
        fil1 = riga.iloc[0]["Filetto_1"]
        gen1 = riga.iloc[0]["Genere_1"]
        fil2 = riga.iloc[0]["Filetto_2"]
        gen2 = riga.iloc[0]["Genere_2"]
        att1 = riga.iloc[0]["Attacco_1"]
        att2 = riga.iloc[0]["Attacco_2"]
        
        nodo1 = (fil1, gen1)
        nodo2 = (fil2, gen2)
        
        if nodo_necessario == nodo1:
            sequenza.append(f"{att1} → {att2}")
            nodo_necessario = (fil2, scambia_genere(gen2))
        elif nodo_necessario == nodo2:
            sequenza.append(f"{att2} → {att1}")
            nodo_necessario = (fil1, scambia_genere(gen1))
        else:
            sequenza.append(f"!!! {att1} → {att2}: ERRORE")
            nodo_necessario = nodo2
    
    return " | ".join(sequenza)

# ---------------------------------------------------------------------------
# INTERFACCIA UTENTE
# ---------------------------------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    attacco_partenza_str = st.selectbox(
        "🔵 Attacco di Partenza (dell'adattatore)",
        options=sorted(anagrafica_attacchi["ATTACCO"].unique())
    )

with col2:
    attacco_arrivo_str = st.selectbox(
        "🔴 Attacco di Arrivo (dell'adattatore)",
        options=sorted(anagrafica_attacchi["ATTACCO"].unique())
    )

with col3:
    max_articoli = st.number_input(
        "⚙️ N° Max Adattatori Combinabili",
        min_value=1,
        max_value=5,
        value=3,
        help="Numero massimo di adattatori nel percorso"
    )

# ---------------------------------------------------------------------------
# RICERCA PERCORSI
# ---------------------------------------------------------------------------
if st.button("🔍 RICERCA ADATTATORI", type="primary", use_container_width=True):
    
    with st.spinner("Ricerca in corso..."):
        
        # Converti attacchi
        attacco_partenza = ricerca_attacco(attacco_partenza_str, anagrafica_attacchi)
        attacco_arrivo = ricerca_attacco(attacco_arrivo_str, anagrafica_attacchi)
        
        # Costruisci grafo
        grafo = costruisci_grafo(df)
        
        # Trova percorsi
        percorsi_trovati = []
        trova_percorsi(attacco_partenza, attacco_arrivo, [], percorsi_trovati, max_articoli, grafo)
        
        # Ordina per numero articoli
        percorsi_trovati = sorted(percorsi_trovati, key=len)
        
        # ---------------------------------------------------------------------------
        # RIMOZIONE PERCORSI DUPLICATI (ordine-indipendenti)
        # ---------------------------------------------------------------------------

        #percorsi_unici = []
        #visti = set()

        #for p in percorsi_trovati:
        #    chiave = tuple(sorted(p))   # stesso set di adattatori = stesso percorso
        #    if chiave not in visti:
        #        visti.add(chiave)
        #        percorsi_unici.append(p)

        #percorsi_trovati = percorsi_unici
    
    # ---------------------------------------------------------------------------
    # RISULTATI
    # ---------------------------------------------------------------------------
    st.markdown("---")
    if len(percorsi_trovati)>1:
        st.subheader(f"📊 Risultati: {len(percorsi_trovati)} combinazioni trovate")
    else:
        st.subheader(f"📊 Risultati: {len(percorsi_trovati)} combinazione trovata")
        
    
    if percorsi_trovati:
        
        # Raggruppa per numero di articoli
        percorsi_per_num = defaultdict(list)
        for p in percorsi_trovati:
            percorsi_per_num[len(p)].append(p)
        
        # Mostra con tabs
        tabs = st.tabs([f"{'⭐' if i==1 else ''} {i} adattator{'i' if i>1 else 'e'} ({len(percorsi_per_num[i])} combinazioni)" 
                       for i in sorted(percorsi_per_num.keys())])
        
        for idx, num_art in enumerate(sorted(percorsi_per_num.keys())):
            with tabs[idx]:
                for i, sequenza_articoli in enumerate(percorsi_per_num[num_art], 1):
                    sequenza_attacchi = stampa_sequenza_attacchi(sequenza_articoli, df, attacco_partenza)
                    
                    with st.expander(f"Combinazione {i}:   {' → '.join(sequenza_articoli)}", expanded=(i<1)):
                        st.markdown(f"**Codici Articolo:**   `{' → '.join(sequenza_articoli)}`")
                        st.markdown(f"**Sequenza Attacchi:**   `{sequenza_attacchi}`")
                        
                        # Dettagli articoli
                        st.markdown("**Dettagli:**")
                        for cd_ar in sequenza_articoli:
                            riga = df[df["Cd_Ar"] == cd_ar].iloc[0]
                            descr = f" | `{riga['DESCRIZIONE']}`" if pd.notna(riga['DESCRIZIONE']) else ""
                            st.markdown(f"- {cd_ar} : `{riga['ATTACCO_1']} ↔ {riga['ATTACCO_2']}`  {descr}")
    else:
        st.warning("⚠️ Nessuna combinazione trovata con gli attacchi selezionati")
        st.info("💡 Prova ad aumentare il numero massimo di adattatori impiegabili (max=3)")

# ---------------------------------------------------------------------------
# SIDEBAR INFO
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("ℹ️ Informazioni")
    st.markdown(f"""
    **Dataset caricato:**
    - {len(df)} adattatori
    - {len(anagrafica_attacchi)} attacchi unici
    
    **Come usare:**
    1. Seleziona attacco di partenza (dell'adattatore desiderato)
    2. Seleziona attacco di arrivo 
    3. Imposta n° max adattori impiegabili
    4. Clicca "RICERCA ADATTATORI"
    
    **Algoritmo:**
    - DFS (Depth-First Search)
    - Ricerca fino a {max_articoli} articoli
    - Compatibilità genere (M↔F)
    """)
    
    st.markdown("---")
    st.markdown("💡 **Nota:** Il database è precaricato ma può essere aggiornato caricando un nuovo file Excel.")
