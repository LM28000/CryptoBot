# Utiliser une image Python légère
FROM python:3.11-slim

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers de dépendances et installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code source
COPY . .

# Exposer le port de Streamlit
EXPOSE 8501

# Lancer le Bot en arrière-plan ET le Dashboard
# On utilise un script shell pour gérer les deux
CMD python script.py & streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0