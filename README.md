# 🔧 Ricerca Adattatori Aste Perforatrici Teleguidate

App Streamlit per trovare combinazioni di adattatori per le aste di perforatrici teleguidate.

## ✨ Caratteristiche

- **Database precaricato**: Include il file `DW_lista_adattatori_completa.xlsx`
- **Caricamento personalizzato**: Possibilità di caricare un file Excel diverso
- **Ricerca intelligente**: Algoritmo DFS per trovare tutti i percorsi possibili
- **Interfaccia intuitiva**: Semplice da usare, risultati chiari

## 📋 Requisiti del File Excel

Il file Excel deve contenere le seguenti colonne nel primo foglio:
- `Cd_Ar` - Codice articolo
- `Filetto_1` - Filetto primo attacco
- `Filetto_2` - Filetto secondo attacco
- `Genere_1` - Genere primo attacco (M/F)
- `Genere_2` - Genere secondo attacco (M/F)
- `Category` - Categoria articolo

E un secondo foglio denominato "FILETTI" contenente:
- `ORDINE` - ordine di visualizzazione dei filetti
- `FILETTI STANDARD` - lista ordinata dei filetti per la visualizzazione

## 🚀 Come usare l'app

1. L'app carica automaticamente il database predefinito
2. Seleziona l'attacco di partenza
3. Seleziona l'attacco di arrivo
4. Imposta il numero massimo di articoli
5. Clicca "CERCA PERCORSI"
6. Propone un file Excel da scaricare con i risultati
7. Propone i risultati sulla schermata

## 💻 Installazione locale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 🌐 Deploy su Streamlit Cloud

1. Carica i file su GitHub
2. Vai su [share.streamlit.io](https://share.streamlit.io)
3. Connetti il repository
4. Deploy!
