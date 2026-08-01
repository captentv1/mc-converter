# Contribuer a MC-Converter

Merci de vouloir aider. Le projet est volontairement 100% local (pas
d'API, pas de service tiers) pour rester utilisable par n'importe qui.

## Lancer les tests

```
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Pistes de contribution

- **`data/mapping/pack_format.json`** : ajouter le `pack_format` de chaque
  nouvelle version Minecraft (source : la page "Pack format" du wiki
  Minecraft). C'est la table la plus simple a maintenir a jour.
- **`core/static_analysis.py`** : detecter plus de signaux utiles dans le
  bytecode (mixins, access transformers, appels reflectifs) pour affiner
  l'estimation de travail sur les conversions cross-loader.
- **Remapping bytecode reel pour Forge <-> NeoForge** : aujourd'hui seul le
  manifest est traduit (`mod_converter.py`). Aller plus loin demande un
  vrai parseur de fichier `.class` (pool de constantes correctement
  reecrit avec sa longueur mise a jour), pas un remplacement de texte —
  une bibliotheque comme `jawa` serait un bon point de depart.
- **Migration de monde** : `world_converter.py` prepare juste la copie et
  documente la commande serveur a lancer. Automatiser le lancement d'un
  serveur vanilla headless (avec acceptation EULA explicite de
  l'utilisateur) irait plus loin.

## Style

- Python 3.11+, type hints, dataclasses pour les structures de donnees.
- Un converter = une classe qui implemente `BaseConverter.convert(job)` et
  renvoie un `ConversionReport` ; ne jamais lever d'exception pour un cas
  attendu (fichier manquant, version inconnue) — remplir `report.status`
  et `report.message` a la place.
- Aucune dependance reseau dans `core/`. Les interfaces (`desktop_app/`,
  `web_app/`) peuvent evoluer independamment tant qu'elles passent par
  `core.orchestrator.CoreEngine`.
