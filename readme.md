# Telegram Daily Briefing Bot (Proof of Concept)

Un assistente personale su Telegram che invia aggiornamenti automatici sul meteo locale e sull'andamento dei mercati finanziari, costruito su un'architettura AWS Serverless.


## 🎯 Cosa fa

* **Sveglia Automatica:** Invia un report completo ogni mattina alle 9:00.
* **Meteo Locale:** Dati in tempo reale e previsioni (Lucca e Pisa).
* **Borsa & Crypto:** Prezzi aggiornati di S&P 500, Oro, Bitcoin, ecc.
* **Interattivo:** Risponde ai comandi tramite bottoni direttamente nella chat.


## 🛠️ Tecnologie usate

* **Linguaggio:** Python 3.12
* **Cloud (AWS):** Lambda, API Gateway, EventBridge
* **Infrastruttura:** Terraform
* **API:** Telegram, OpenWeather, Finnhub

## ⚙️ Flusso Architetturale

* **EventBridge:** scatena un evento ogni mattina alle 9:00
* **AWS Lambda:** (in Python): interroga le API esterne (OpenWeather, Finnhub) e impagina il report
* **API Gateway:** espone gli endpoint per ricevere i messaggi da Telegram (bottoni)


## 💻 Deploy dell'Infrastruttura
E' possibile replicare l'ambiente usando Terraform:

* Inserimento delle chiavi API nel file `terraform.tfvars` (nascosto).
* Inizializzazione: `terraform init`
* Verifica del piano: `terraform plan`
* Deploy su AWS: `terraform apply`


🚀 Costruito per imparare. Questo bot rappresenta il mio approccio pratico all'infrastruttura Cloud Serverless e all'Infrastructure as Code (IaC), supportato dall'AI per accelerare lo studio e il troubleshooting.