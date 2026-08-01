# MC-Converter

Convertisseur de version / loader pour Minecraft Java (mods, modpacks, mondes, resource packs).

100% local : aucun appel reseau, aucune cle API. Pense pour tourner tel
quel une fois publie en open source, sans compte ni service tiers a
configurer.

## Structure

```
mc-converter/
  core/                    moteur partage (utilise par les deux interfaces)
    job.py                 ConversionJob / ConversionReport (contrat de donnees)
    mapping.py             tables versions <-> pack_format, compat entre loaders
    static_analysis.py     scan hors-ligne du bytecode (aucun reseau/API)
    orchestrator.py        CoreEngine : dispatch vers le bon converter
    converters/
      mod_converter.py         bump de version, repackage Fabric<->Quilt,
                                traduction de manifest Forge<->NeoForge
      modpack_converter.py     applique mod_converter a tout un dossier mods/
      world_converter.py       prepare la copie ; la vraie migration est faite par le jeu
      resourcepack_converter.py  met a jour pack_format (dossier ou .zip)
  data/mapping/            tables JSON (pack_format.json, loaders.json)
  desktop_app/main.py      interface PyQt6
  web_app/                 interface Flask locale
  tests/                   suite pytest sur le moteur (core/)
```

## Installation

```
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Lancer

Desktop :
```
python desktop_app\main.py
```

Web (http://127.0.0.1:5090) :
```
python web_app\app.py
```

## Tests

```
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## Conversion entre types de loader

| Paire | Ce qui est automatique | Ce qui reste manuel |
|---|---|---|
| Meme loader, version differente | Contrainte de version MC dans le manifest | — |
| Fabric <-> Quilt | Rien a faire : Quilt charge nativement un jar Fabric | — |
| Forge <-> NeoForge | Renommage du manifest (`mods.toml` <-> `neoforge.mods.toml`), dependance de loader renommee, contrainte de version MC mise a jour | `loaderVersion` et plages de version specifiques a verifier ; le **code** (`net.minecraftforge.*` vs `net.neoforged.*`) n'est pas reecrit |
| Forge/NeoForge <-> Fabric/Quilt | Rien : API totalement differentes | Portage manuel complet |

Pour les deux derniers cas, le rapport inclut une **analyse statique
locale** (`core/static_analysis.py`) : elle scanne les `.class` du jar a la
recherche de references aux paquets `net/minecraftforge`, `net/neoforged`,
`net/fabricmc`, `org/quiltmc`, pour montrer precisement quelle API le mod
utilise. Aucune tentative de reecrire le bytecode a l'aveugle : un simple
remplacement de texte dans un `.class` compile corromprait le fichier
(le pool de constantes est prefixe par une longueur en octets qui ne serait
plus a jour).

## Portee reelle

- **Automatisable** : bump de version dans un manifest (mod, modpack), pack_format
  d'un resource pack, repackage Fabric<->Quilt.
- **Assiste** : traduction de manifest Forge<->NeoForge (code a porter a la main),
  mise a niveau d'un monde (le convertisseur prepare la copie, le jeu fait la
  migration reelle des chunks), modpack avec mods sans equivalent direct.
- **Non automatisable** : reecrire le code d'un mod entre loaders aux API
  totalement differentes (Forge/NeoForge <-> Fabric/Quilt) — l'analyse
  statique locale aide a estimer le travail, mais la reecriture reste manuelle.

## Contribuer

Projet ouvert a tous, voir [CONTRIBUTING.md](CONTRIBUTING.md).
