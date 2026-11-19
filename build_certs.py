#!/usr/bin/env python3
"""
build_certs.py — turn the real certificate PDFs in certs/ into web assets and a
manifest that customize.py wires into every tab.

For each PDF it emits into site/_res/:
    cert_<key>.jpg      full certificate image   (~1400px wide, for View preview)
    cert_<key>_t.jpg    thumbnail                (~360px wide, for cards/sidebar)
    cert_<key>.pdf      a copy of the real PDF    (what "View certificate" opens)
and writes site/_res/certs.json describing each specialization + its courses.

Source of truth:
    certs/devops/NN_*.pdf   15 course certs (01-15) + spec cert (16), IBM
    certs/fintech/NN_*.pdf   4 course certs (02-05) + spec cert (01), U-Michigan
    certs/michigan.png       cropped U-Michigan partner logo

Run after build_site.py + localize_assets.py, before customize.py.
"""
import json
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CERTS = os.path.join(HERE, "certs")
RES = os.path.join(HERE, "site", "_res")

IBM_LOGO = "/_res/5130a1da15a2db91.png"      # already localized from the capture
MICH_LOGO = "/_res/michigan.png"             # copied in from certs/michigan.png

# ---- real certificate metadata (title / completion month / file) --------------
# order matters: it mirrors the course order inside each specialization block.

DEVOPS = {
    "slug": "devops-and-software-engineering",
    "name": "IBM DevOps and Software Engineering",
    "partner": "IBM",
    "logo": IBM_LOGO,
    "dir": "devops",
    "spec_file": "16_IBM_DevOps_and_Software_Engineering_Professional_Certificate_Atharva_Bobde.pdf",
    "spec_date": "November 2026",
    "courses": [
        ("Introduction to DevOps", "01_Introduction_to_DevOps_Atharva_Bobde.pdf", "November 2026"),
        ("Introduction to Cloud Computing", "02_Introduction_to_Cloud_Computing_Atharva_Bobde.pdf", "November 2026"),
        ("Introduction to Agile Development and Scrum", "03_Introduction_to_Agile_Development_and_Scrum_Atharva_Bobde.pdf", "November 2026"),
        ("Introduction to Software Engineering", "04_Introduction_to_Software_Engineering_Atharva_Bobde.pdf", "November 2026"),
        ("Getting Started with Git and GitHub", "05_Getting_Started_with_Git_and_GitHub_Atharva_Bobde.pdf", "November 2026"),
        ("Hands-on Introduction to Linux Commands and Shell Scripting", "06_Hands-on_Introduction_to_Linux_Commands_and_Shell_Scripting_Atharva_Bobde.pdf", "November 2026"),
        ("Python for Data Science & AI: Hands-On Development", "07_Python_for_Data_Science_and_AI_Hands-On_Development_Atharva_Bobde.pdf", "November 2026"),
        ("Build & Deploy AI Applications with Python & Flask", "08_Build_and_Deploy_AI_Applications_with_Python_and_Flask_Atharva_Bobde.pdf", "November 2026"),
        ("Introduction to Containers w/ Docker, Kubernetes & OpenShift", "09_Introduction_to_Containers_Docker_Kubernetes_OpenShift_Atharva_Bobde.pdf", "November 2026"),
        ("Application Development using Microservices and Serverless", "10_Application_Development_using_Microservices_and_Serverless_Atharva_Bobde.pdf", "November 2026"),
        ("Introduction to Test and Behavior Driven Development", "11_Introduction_to_Test_and_Behavior_Driven_Development_Atharva_Bobde.pdf", "November 2026"),
        ("Continuous Integration and Continuous Delivery (CI/CD)", "12_Continuous_Integration_and_Continuous_Delivery_CICD_Atharva_Bobde.pdf", "November 2026"),
        ("Application Security for Developers and DevOps Professionals", "13_Application_Security_for_Developers_and_DevOps_Professionals_Atharva_Bobde.pdf", "November 2026"),
        ("Monitoring and Observability for Development and DevOps", "14_Monitoring_and_Observability_for_Development_and_DevOps_Atharva_Bobde.pdf", "November 2026"),
        ("DevOps Capstone Project", "15_DevOps_Capstone_Project_Atharva_Bobde.pdf", "November 2026"),
    ],
}

FINTECH = {
    "slug": "fintech",                       # relabels the captured HKUST fintech block
    "name": "Financial Technology (Fintech) Innovations",
    "partner": "University of Michigan",
    "logo": MICH_LOGO,
    "dir": "fintech",
    "spec_file": "01_Financial_Technology_Fintech_Innovations_Specialization_Atharva_Bobde.pdf",
    "spec_date": "November 2026",
    "courses": [
        ("The Future of Payment Technologies", "02_The_Future_of_Payment_Technologies_Atharva_Bobde.pdf", "October 2026"),
        ("Blockchain and Cryptocurrency Explained", "03_Blockchain_and_Cryptocurrency_Explained_Atharva_Bobde.pdf", "November 2026"),
        ("Raising Capital: Credit Tech, Coin Offerings, and Crowdfunding", "04_Raising_Capital_Credit_Tech_Coin_Offerings_and_Crowdfunding_Atharva_Bobde.pdf", "October 2026"),
        ("Innovations in Investment Technology: Artificial Intelligence", "05_Innovations_in_Investment_Technology_Artificial_Intelligence_Atharva_Bobde.pdf", "October 2026"),
    ],
}

SPECS = [DEVOPS, FINTECH]


def render(pdf_path, key):
    """pdf -> full jpg + thumb jpg + pdf copy in site/_res. returns asset paths."""
    full_base = os.path.join(RES, f"cert_{key}")
    subprocess.run(["pdftocairo", "-jpeg", "-singlefile", "-scale-to-x", "1400",
                    "-scale-to-y", "-1", pdf_path, full_base],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    thumb_base = os.path.join(RES, f"cert_{key}_t")
    subprocess.run(["pdftocairo", "-jpeg", "-singlefile", "-scale-to-x", "360",
                    "-scale-to-y", "-1", pdf_path, thumb_base],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.copyfile(pdf_path, os.path.join(RES, f"cert_{key}.pdf"))
    return (f"/_res/cert_{key}.jpg", f"/_res/cert_{key}_t.jpg", f"/_res/cert_{key}.pdf")


def main():
    if not os.path.isdir(RES):
        raise SystemExit("[!] site/_res not found — run build_site.py + localize_assets.py first")
    # drop any cert assets from a previous build so stale files never linger
    for f in os.listdir(RES):
        if f.startswith("cert_") or f == "certs.json":
            os.remove(os.path.join(RES, f))
    # partner logo for the relabeled spec
    mich = os.path.join(CERTS, "michigan.png")
    if os.path.exists(mich):
        shutil.copyfile(mich, os.path.join(RES, "michigan.png"))

    manifest = {"specs": {}}
    for spec in SPECS:
        sdir = os.path.join(CERTS, spec["dir"])
        key = spec["dir"]
        img, thumb, pdf = render(os.path.join(sdir, spec["spec_file"]), f"{key}_spec")
        entry = {
            "name": spec["name"], "partner": spec["partner"], "logo": spec["logo"],
            "spec": {"img": img, "thumb": thumb, "pdf": pdf, "date": spec["spec_date"]},
            "courses": [],
        }
        for i, (title, fname, date) in enumerate(spec["courses"], 1):
            img, thumb, pdf = render(os.path.join(sdir, fname), f"{key}_{i:02d}")
            entry["courses"].append({"title": title, "img": img, "thumb": thumb,
                                     "pdf": pdf, "date": date})
        manifest["specs"][spec["slug"]] = entry
        print(f"[+] {spec['name']}: spec + {len(entry['courses'])} course certs")

    with open(os.path.join(RES, "certs.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[done] certs.json written — {sum(len(s['courses']) for s in manifest['specs'].values())} course + "
          f"{len(manifest['specs'])} spec certs rendered")


if __name__ == "__main__":
    main()
