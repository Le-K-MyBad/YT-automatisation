#!/usr/bin/env python3
"""Test complet du script d'automatisation YouTube."""

import sys
import os
import shutil
from pathlib import Path

def test_full_script():
    """Test complet du script d'automatisation."""
    print("=" * 60)
    print("TEST COMPLET DU SCRIPT D'AUTOMATISATION YOUTUBE")
    print("=" * 60)

    # Étape 1: Vérifier l'environnement
    print("\n1. VÉRIFICATION DE L'ENVIRONNEMENT")
    print("-" * 40)

    # Vérifier Python
    print(f"✓ Python: {sys.version}")

    # Vérifier les imports
    try:
        import yaml
        print("✓ PyYAML importé")
    except ImportError:
        print("✗ PyYAML non disponible")
        return False

    try:
        import yt_dlp
        print(f"✓ yt-dlp importé (version: {yt_dlp.version.__version__})")
    except ImportError:
        print("✗ yt-dlp non disponible")
        return False

    # Vérifier selenium (optionnel)
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        print("✓ Selenium disponible")
        selenium_available = True
    except ImportError:
        print("⚠ Selenium non disponible (optionnel)")
        selenium_available = False

    # Étape 2: Tester la configuration
    print("\n2. TEST DE LA CONFIGURATION")
    print("-" * 40)

    try:
        sys.path.insert(0, 'scripts')
        from automation import load_config, is_chrome_available
        print("✓ Module automation importé")

        config = load_config()
        print(f"✓ Configuration chargée: {list(config.keys())}")

        # Vérifier les chemins
        relaxing_video = Path(config.get('relaxing_video', 'relaxing.mp4'))
        print(f"✓ Vidéo relaxing: {relaxing_video} (existe: {relaxing_video.exists()})")

        output_dir = Path(config.get('output_dir', 'output'))
        print(f"✓ Dossier output: {output_dir}")

        # Vérifier Chrome
        chrome_ok = is_chrome_available()
        print(f"✓ Chrome disponible: {chrome_ok}")

        # Vérifier cookies
        cookies_file = config.get('youtube_cookies_file')
        if cookies_file:
            cookies_path = Path(cookies_file)
            if not cookies_path.is_absolute():
                cookies_path = Path('.') / cookies_file
            cookies_exist = cookies_path.exists()
            print(f"✓ Cookies configurés: {cookies_file} (existe: {cookies_exist})")
            if cookies_exist:
                with open(cookies_path, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    print(f"  - {len(lines)} lignes de cookies valides")
        else:
            print("⚠ Aucun fichier cookies configuré")

    except Exception as e:
        print(f"✗ Erreur configuration: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Étape 3: Test de téléchargement
    print("\n3. TEST DE TÉLÉCHARGEMENT")
    print("-" * 40)

    # Nettoyer le dossier output
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Tester avec une vidéo normale d'abord
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley (devrait marcher)
        "https://www.youtube.com/shorts/hj_mb_1GvL0",  # Short (risque d'échouer sans cookies)
    ]

    from automation import download_video

    for url in test_urls:
        print(f"\nTest de: {url}")
        print("-" * 30)

        try:
            result_file = download_video(url, output_dir, config)

            if result_file and result_file.exists():
                size = result_file.stat().st_size
                print(f"✓ Téléchargement réussi: {result_file.name}")
                print(f"  - Taille: {size} bytes ({size/1024/1024:.1f} MB)")
                if size > 10000:  # Au moins 10KB
                    print("  - Fichier valide ✓")
                else:
                    print("  - Fichier trop petit ⚠")
            else:
                print("✗ Aucun fichier retourné")

        except Exception as e:
            print(f"✗ Échec: {e}")
            import traceback
            traceback.print_exc()

    # Étape 4: Vérifier les fichiers créés
    print("\n4. FICHIERS CRÉÉS")
    print("-" * 40)

    if output_dir.exists():
        files = list(output_dir.glob("*"))
        if files:
            print(f"✓ {len(files)} fichier(s) dans output/:")
            for f in files:
                size = f.stat().st_size
                print(f"  - {f.name}: {size} bytes")
        else:
            print("✗ Aucun fichier dans output/")
    else:
        print("✗ Dossier output n'existe pas")

    print("\n" + "=" * 60)
    print("TEST TERMINÉ")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = test_full_script()
    sys.exit(0 if success else 1)