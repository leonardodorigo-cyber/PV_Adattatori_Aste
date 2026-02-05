import streamlit as st
import pandas as pd
from collections import defaultdict
import os

# Configurazione pagina
st.set_page_config(page_title="Ricerca Percorsi Adattatori", layout="wide")

# ---------------------------------------------------------------------------
# TITOLO
# ---------------------------------------------------------------------------
st.title("🔧 Drilling Adapter Finder")
st.markdown("---")

# ---------------------------------------------------------------------------
# FUNZIONI CARICAMENTO DATI
# ---------------------------------------------------------------------------

@st.cache_data
def carica_dati(file_path=None, uploaded_file=None):
    
    """Carica i dati da file locale o da upload"""
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
    elif file_path is not None and os.path.exists(file_path):
        xls = pd.ExcelFile(file_path)
    else:
        return None, None

    df = pd.read_excel(xls, sheet_name=0)

    ordine_attacchi = None
    if "FILETTI" in xls.sheet_names:
        try:
            ordine_attacchi = pd.read_excel(xls, sheet_name=1)
            # ordine_attacchi = pd.read_excel(xls, sheet_name="FILETTI")
            # accetta solo se le colonne esistono
            if {"ORDINE", "FILETTI STANDARD"}.issubset(ordine_attacchi.columns):
                ordine_attacchi = ordine_attacchi[["ORDINE", "FILETTI STANDARD"]]
                filetti_trovati = True
            else:
                ordine_attacchi = None
                filetti_trovati = False
    
        except Exception:
            ordine_attacchi = None
            filetti_trovati = False
    else:
        filetti_trovati = False
        
    ## ✅ DEBUG: Stampa info sul DataFrame
    # st.write("=== DEBUG INFO ===")
    # st.write(f"Colonne disponibili: {df.columns.tolist()}")
    # st.write(f"Righe totali: {len(df)}")
    # st.write(f"Righe con Cd_Ar NaN: {df['Cd_Ar'].isna().sum()}")
    # st.write(f"Prime 5 righe Cd_Ar:\n{df['Cd_Ar'].head()}")
    # st.write("==================")

    # Creazione colonne "ATTACCO_1" e "ATTACCO_2"
    df["ATTACCO_1"] = df["Filetto_1"].astype(str).str.strip() + " " + df["Genere_1"].astype(str).str.strip()
    df["ATTACCO_2"] = df["Filetto_2"].astype(str).str.strip() + " " + df["Genere_2"].astype(str).str.strip()
    
    # Creazione THREAD_INFO come in Excel
    df["THREAD_INFO"] = df["ATTACCO_1"] + " / " + df["ATTACCO_2"]
    
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
    
    return df, anagrafica_attacchi, ordine_attacchi, filetti_trovati

@st.cache_data
def carica_giacenze(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        df_giac = pd.read_excel(uploaded_file)

        colonne_richieste = {
            "Cd_AR",
            "Cd_MG",
            "GIacenza",
            "DispImmediata",
            "Disp"
        }

        colonne_presenti = set(df_giac.columns)

        if not colonne_richieste.issubset(colonne_presenti):
            colonne_mancanti = colonne_richieste - colonne_presenti
            st.error(
                f"❌ File giacenze non valido. Colonne mancanti: {', '.join(colonne_mancanti)}"
            )
            return None

        # Pulizia minima
        df_giac["Cd_AR"] = df_giac["Cd_AR"].astype(str).str.strip()
        df_giac["Cd_MG"] = df_giac["Cd_MG"].astype(str).str.strip().str.zfill(5)

        return df_giac

    except Exception as e:
        st.error(f"❌ Errore nel caricamento file giacenze: {e}")
        return None

# ---------------------------------------------------------------------------
# FUNZIONE CALCOLO SEMAFORO DISPONIBILITÀ
# ---------------------------------------------------------------------------

def calcola_disponibilita(cd_ar, df_giacenze):
    """
    Calcola il semaforo di disponibilità per un articolo.
    
    Returns:
        tuple: (emoji_semaforo, tooltip_text)
    """
    if df_giacenze is None or df_giacenze.empty:
        return "⚪", "Giacenze non caricate"
    
    # Normalizza il codice articolo (rimuovi eventuali prefissi e spazi)
    cd_ar_clean = str(cd_ar).strip()
    
    # Prova prima il match esatto
    righe_articolo = df_giacenze[df_giacenze["Cd_AR"] == cd_ar_clean]
    
    # Se non trova nulla, prova senza prefisso "DWAR-"
    if righe_articolo.empty and cd_ar_clean.startswith("DWAR-"):
        cd_ar_no_prefix = cd_ar_clean.replace("DWAR-", "")
        righe_articolo = df_giacenze[df_giacenze["Cd_AR"] == cd_ar_no_prefix]
    
    if righe_articolo.empty:
        return "🔴", "Articolo non trovato in giacenze"
    
    # Verifica condizione VERDE: DispImmediata > 0 nel magazzino 00001
    mag_00001 = righe_articolo[righe_articolo["Cd_MG"] == "00001"]
    if not mag_00001.empty:
        disp_immediata_00001 = mag_00001["DispImmediata"].sum()
        if disp_immediata_00001 > 0:
            return "🟢", f"Disponibile a scaffale: {int(disp_immediata_00001)} pz"
    
    # Verifica condizione ROSSA: Disp <= 0 in tutti i magazzini
    disp_totale = righe_articolo["Disp"].sum()
    if disp_totale <= 0:
        return "🔴", "Non disponibile in nessun magazzino"
    
    # Altrimenti GIALLO (disponibile ma non a scaffale o non immediata)
    # Costruisci messaggio dettagliato
    info_magazzini = []
    for _, riga in righe_articolo.iterrows():
        mag = riga["Cd_MG"]
        disp = riga["Disp"]
        if disp > 0:
            if mag in ["00230", "00240"]:
                info_magazzini.append(f"Montato (MG {mag}): {int(disp)} pz")
            else:
                info_magazzini.append(f"MG {mag}: {int(disp)} pz")
    
    tooltip = " | ".join(info_magazzini) if info_magazzini else "Disponibile (non a scaffale)"
    return "🟡", tooltip

# ---------------------------------------------------------------------------
# CARICAMENTO DATI
# ---------------------------------------------------------------------------

# Tentativo di caricare il file predefinito
FILE_EXCEL = "DW_lista_adattatori_completa.xlsx"
df, anagrafica_attacchi, ordine_attacchi, filetti_trovati = carica_dati(file_path=FILE_EXCEL)

# Se il file predefinito non esiste, blocca l'app
if df is None:
    st.error(f"❌ File predefinito '{FILE_EXCEL}' non trovato. L'app si interrompe.")
    st.stop()

if not filetti_trovati:
    st.warning(
        "⚠️ Foglio **'FILETTI STANDARD'** non trovato o non valido.\n\n"
        "➡️ Gli attacchi verranno mostrati in **ordine alfabetico**, se l'errore persiste contattare l'admin."
    )

# Se il file esiste, procedi
# st.success(f"✅ Database caricato: {len(df)} adattatori disponibili")

# ---------------------------------------------------------------------------
# CARICAMENTO GIACENZE
# ---------------------------------------------------------------------------

# st.markdown("---")
st.subheader("📦 Disponibilità Magazzino (opzionale)")

uploaded_giac = st.file_uploader(
    "Carica file Excel con giacenze",
    type=["xlsx"],
    help="Colonne richieste: Cd_AR, Cd_MG, GIacenza, DispImmediata, Disp"
)

df_giac = carica_giacenze(uploaded_giac)

# if df_giac is not None:
#     st.success(f"✅ File giacenze caricato: {len(df_giac)} righe")
# else:
#     st.info("ℹ️ Nessun file giacenze caricato")

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
        art = row['ARTICOLO']
        
        grafo[(f1, g1)].append(((f2, g2), (cd_ar, art)))
        grafo[(f2, g2)].append(((f1, g1), (cd_ar, art)))
    
    return grafo

def trova_percorsi(nodo_corrente, nodo_arrivo, articoli_usati, percorsi_trovati, max_articoli, grafo):

    # Se siamo arrivati al nodo finale (con almeno un adattatore), salva percorso
    if nodo_corrente == (nodo_arrivo[0], scambia_genere(nodo_arrivo[1])) and len(articoli_usati) > 0:
        percorsi_trovati.append(list(articoli_usati))
        return

    # Stop se superiamo numero massimo articoli
    if len(articoli_usati) >= max_articoli:
        return
    
    for vicino, info_articolo in grafo[nodo_corrente]:
        cd_ar, articolo = info_articolo
        
        # evita di riusare lo stesso articolo
        if cd_ar in articoli_usati: # se vuoi stampare il codice articolo CON prefisso
        # if articolo in articoli_usati: # se vuoi stampare il codice articolo SENZA prefisso
            continue
        
        nuovo_nodo_corrente = (vicino[0], scambia_genere(vicino[1]))
        articoli_usati.append(cd_ar) # se vuoi stampare il codice articolo CON prefisso
        # articoli_usati.append(articolo) # se vuoi stampare il codice articolo SENZA prefisso
        trova_percorsi(nuovo_nodo_corrente, nodo_arrivo, articoli_usati, percorsi_trovati, max_articoli, grafo)
        articoli_usati.pop()

def stampa_sequenza_attacchi(sequenza_articoli, df, attacco_partenza):
    sequenza = []
    nodo_necessario = attacco_partenza
    
    for cd_ar in sequenza_articoli: # se vuoi stampare il codice articolo CON prefisso
    # for articolo in sequenza_articoli: # se vuoi stampare il codice articolo SENZA prefisso

        # Recupero riga articolo dal DataFrame
        riga = df[df["Cd_Ar"] == cd_ar] # se vuoi stampare il codice articolo CON prefisso
        # riga = df[df["ARTICOLO"] == articolo] # se vuoi stampare il codice articolo SENZA prefisso

        if riga.empty:
            return f"❌ ERRORE: Codice articolo {cd_ar} non trovato nel dataset" # se vuoi stampare il codice articolo CON prefisso
            # return f"❌ ERRORE: Codice articolo {articolo} non trovato nel dataset" # se vuoi stampare il codice articolo SENZA prefisso
        
        riga = riga.iloc[0]
        
        fil1 = riga["Filetto_1"]
        gen1 = riga["Genere_1"]
        fil2 = riga["Filetto_2"]
        gen2 = riga["Genere_2"]
        att1 = riga["Attacco_1"]
        att2 = riga["Attacco_2"]
        
        nodo1 = (fil1, gen1)
        nodo2 = (fil2, gen2)
        
        if nodo_necessario == nodo1:
            sequenza.append(f"{att1} | {att2}")
            nodo_necessario = (fil2, scambia_genere(gen2))
        elif nodo_necessario == nodo2:
            sequenza.append(f"{att2} | {att1}")
            nodo_necessario = (fil1, scambia_genere(gen1))
        else:
            sequenza.append(f"!!! {att1} | {att2}: ERRORE")
            nodo_necessario = nodo2
    
    return " → ".join(sequenza)


# ---------------------------------------------------------------------------
# COSTRUZIONE ELENCO ORDINATO ATTACCHI
# ---------------------------------------------------------------------------

# attacchi_ordinati = sorted(anagrafica_attacchi["ATTACCO"].unique())

attacchi_disponibili = anagrafica_attacchi["ATTACCO"].unique().tolist()
attacchi_disponibili = [a for a in attacchi_disponibili if isinstance(a, str) and a.strip() != ""]

if ordine_attacchi is not None and not ordine_attacchi.empty:
    ordine_attacchi = ordine_attacchi.dropna(subset=["FILETTI STANDARD"])
    ordine_attacchi["FILETTI STANDARD"] = ordine_attacchi["FILETTI STANDARD"].str.strip()

    lista_prioritaria = []

    for filetto in ordine_attacchi["FILETTI STANDARD"]:
        # Genera ATTACCHI completo per tutti i generi comuni
        for genere in ["M", "F"]:
            attacco_completo = f"{filetto} {genere}"
            lista_prioritaria.append(attacco_completo)

    # prima quelli ordinati, poi gli altri
    attacchi_ordinati = (
        [a for a in lista_prioritaria if a in attacchi_disponibili] +
        sorted([a for a in attacchi_disponibili if a not in lista_prioritaria])
    )
else:
    attacchi_ordinati = sorted(attacchi_disponibili)

# ---------------------------------------------------------------------------
# INTERFACCIA UTENTE
# ---------------------------------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    attacco_partenza_str = st.selectbox(
        "🔵 Attacco di Partenza (dell'adattatore)",
        options=attacchi_ordinati,
        index=18 if len(attacchi_ordinati) > 17 else 0  # fallback se lista troppo corta
    )

with col2:
    attacco_arrivo_str = st.selectbox(
        "🔴 Attacco di Arrivo   (dell'adattatore)",
        options=attacchi_ordinati,
        index=18 if len(attacchi_ordinati) > 17 else 0  # fallback se lista troppo corta
    )

with col3:
    max_articoli = st.number_input(
        "⚙️ N° Max Adattatori",
        min_value=1,
        max_value=3,
        value=3,
        help="Numero massimo di adattatori che si desidera combinare (max 3)"
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
        
        # # ✅ DEBUG: Controlliamo cosa contengono i percorsi
        # st.write("DEBUG - Primi 3 percorsi trovati:")
        # for idx, p in enumerate(percorsi_trovati[:3]):
        #     st.write(f"Percorso {idx}: {p} | Tipo: {[type(x) for x in p]}")
        
        # ---------------------------------------------------------------------------
        # RIMOZIONE PERCORSI DUPLICATI (ordine-indipendenti)
        # ---------------------------------------------------------------------------

        percorsi_unici = []
        visti = set()

        for p in percorsi_trovati:
            chiave = tuple(sorted(p))   # stesso set di adattatori = stesso percorso
            if chiave not in visti:
                visti.add(chiave)
                percorsi_unici.append(p)

        percorsi_trovati = percorsi_unici
    
    # ---------------------------------------------------------------------------
    # RISULTATI
    # ---------------------------------------------------------------------------
    st.markdown("---")
    if len(percorsi_trovati)>1:
        st.subheader(f"📊 Risultati: {len(percorsi_trovati)} combinazioni trovate")
    else:
        st.subheader(f"📊 Risultati: {len(percorsi_trovati)} combinazione trovata")
        
    # ---------------------------------------------------------------------------
    # DOWNLOAD EXCEL
    # ---------------------------------------------------------------------------
    
    if percorsi_trovati:
    
        # Crea DataFrame per export
        risultati_export = []
        
        for p in percorsi_trovati:
            # Crea una riga con max 5 colonne (adattatore_1, adattatore_2, ecc.)
            riga = {
                'Adattatore_1': p[0] if len(p) > 0 else None,
                'Adattatore_2': p[1] if len(p) > 1 else None,
                'Adattatore_3': p[2] if len(p) > 2 else None,
                'Adattatore_4': p[3] if len(p) > 3 else None,
                'Adattatore_5': p[4] if len(p) > 4 else None,
                'n_adattatori': len(p)
            }
            risultati_export.append(riga)
        
        df_export = pd.DataFrame(risultati_export)
        
        # Rimuovi colonne completamente vuote
        df_export = df_export.dropna(axis=1, how='all')
        
        # Converti in Excel
        from io import BytesIO
        from openpyxl.styles import Alignment
        from openpyxl.utils import get_column_letter
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Combinazioni')
            worksheet = writer.sheets['Combinazioni']
        
            # --- Imposta larghezza colonne ---
            colonne_adattatori = [c for c in df_export.columns if c.startswith("Adattatore_")]
            larghezza_adattatori = 18  # puoi regolare
            
            for idx, col in enumerate(df_export.columns, start=1):
                lettera = get_column_letter(idx)
                if col in colonne_adattatori:
                    worksheet.column_dimensions[lettera].width = larghezza_adattatori
                else:
                    worksheet.column_dimensions[lettera].width = 14
            
            # --- Freeze e filtro ---
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
        
            # --- Allinea i titoli a sinistra ---
            for cella in worksheet[1]:  # la prima riga = header
                cella.alignment = Alignment(horizontal='left')
        
        buffer.seek(0)
        
        st.markdown("---")
        
        # Bottone download
        st.download_button(
            label="📥 Scarica Risultati (Excel)",
            data=buffer,
            file_name=f"combinazioni_[{attacco_partenza_str}]_[{attacco_arrivo_str}].xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.markdown("---")

    # ---------------------------------------------------------------------------
    # RISULTATI
    # ---------------------------------------------------------------------------
    
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
                    
                    with st.expander(f"Combinazione {i}:   `{' → '.join(sequenza_articoli)}`", expanded=True):
                    # with st.expander(f"Combinazione {i}:   `{sequenza_attacchi}` ", expanded=True):
                        # st.markdown(f"**Codici Articolo:**   `{' → '.join(sequenza_articoli)}`")
                        st.markdown(f"**Sequenza Attacchi:**   `{sequenza_attacchi}`")
                        
                        # Dettagli articoli
                        # st.markdown("**Dettagli:**")
                        # for cd_ar in sequenza_articoli:
                        #     riga = df[df["Cd_Ar"] == cd_ar].iloc[0]
                            # descr = f" | `{riga['DESCRIZIONE']}`" if pd.notna(riga['DESCRIZIONE']) else ""
                            # st.markdown(f"- {cd_ar} : `{riga['ATTACCO_1']} ↔ {riga['ATTACCO_2']}`  {descr}")
                            # descr = f"`{riga['DESCRIZIONE']}` | " if pd.notna(riga['DESCRIZIONE']) else ""
                            # descr = f"`{riga['Category']}` | " if pd.notna(riga['Category']) else ""
                            # st.markdown(f"- {cd_ar} :  {descr}  `{riga['ATTACCO_1']} ↔ {riga['ATTACCO_2']}`")

                        # st.markdown(f"**Sequenza Attacchi:**   `{sequenza_attacchi}`")

                        # Crea lista dei dettagli CON SEMAFORO DISPONIBILITÀ
                        dettagli = []
                        
                        for cd_ar in sequenza_articoli: # se vuoi stampare il codice articolo CON prefisso
                        # for articolo in sequenza_articoli: # se vuoi stampare il codice articolo SENZA prefisso
                            
                            riga_df = df[df["Cd_Ar"] == cd_ar]  # se vuoi stampare il codice articolo CON prefisso
                            # riga_df = df[df["ARTICOLO"] == articolo]  # se vuoi stampare il codice articolo SENZA prefisso
                            
                            if not riga_df.empty:
                                riga = riga_df.iloc[0]
                                
                                # Calcola semaforo disponibilità
                                semaforo, tooltip = calcola_disponibilita(cd_ar, df_giac)
                                
                                dettagli.append({
                                    "Disp.": semaforo,
                                    "Articolo": cd_ar, # se vuoi stampare il codice articolo CON prefisso
                                    # "Articolo": articolo, # se vuoi stampare il codice articolo SENZA prefisso
                                    "Categoria": riga['Category'].strip() if pd.notna(riga['Category']) else "",
                                    "Thread Info": riga['THREAD_INFO'] if pd.notna(riga['THREAD_INFO']) else "",
                                    "Info Disponibilità": tooltip
                                })
    
                        # Crea DataFrame per la tabella
                        df_tabella = pd.DataFrame(dettagli)
                        
                        # Mostra tabella in Streamlit
                        st.table(df_tabella)
    
    else:
        st.warning("⚠️ Nessuna combinazione trovata con gli attacchi selezionati")
        st.info("💡 Prova ad aumentare il numero massimo di adattatori impiegabili (max=3)")

# ---------------------------------------------------------------------------
# SIDEBAR INFO
# ---------------------------------------------------------------------------
with st.sidebar:

    st.header("📊 Stato Dati")

    # Database principale
    if df is not None:
        st.success(f"Database caricato ({len(df)} righe)")
    else:
        st.error("Database adattatori NON caricato")

    # Giacenze (opzionale)
    if df_giac is not None:
        st.success(f"Giacenze caricate ({len(df_giac)} righe)")
    else:
        st.info("Giacenze non caricate")
        
    st.header("ℹ️ Informazioni")
    st.markdown(f"""
    **Come usare:**
    1. Seleziona attacco di partenza (dell'adattatore desiderato)
    2. Seleziona attacco di arrivo 
    3. Imposta n° max adattori impiegabili
    4. Clicca "RICERCA ADATTATORI"

    **Risultati:**
    - Verranno mostrate tutte le combinazioni possibili.
    - Ogni combinazione mostra la **sequenza degli attacchi** e i dettagli di ciascun articolo impiegato.
    - È possibile scaricare tutte le combinazioni in un **file Excel**.
    
    **Semaforo Disponibilità:**
    - 🟢 **Verde**: Disponibile a scaffale (magazzino 00001)
    - 🟡 **Giallo**: Disponibile ma non a scaffale (es. montato in macchina)
    - 🔴 **Rosso**: Non disponibile o non trovato in giacenze
    - ⚪ **Bianco**: File giacenze non caricato
    """)
    
    st.markdown("---")
    st.markdown("💡 **Nota:** Se si osservano errori nelle combinazioni o articoli mancanti si prega di contattare l'admin.")
