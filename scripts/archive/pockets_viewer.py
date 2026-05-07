"""pockets_viewer.py - Visualizar configuración de pockets de forma clara"""
import yaml
import json

def load_pockets_config(file_path="pockets_config.yaml"):
    """Load pockets configuration from YAML"""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def print_pocket_summary(config):
    """Print summary of all pockets"""
    print("\n" + "=" * 100)
    print("🎯 CONFIGURACIÓN DE 7 POCKETS TEMÁTICOS - LITERATURA REVIEW BID-IA")
    print("=" * 100)

    pockets = config['pockets']
    for i, (pocket_id, pocket) in enumerate(pockets.items(), 1):
        status = "✅" if pocket['status'] == 'active' else "⏸️"
        priority = pocket['priority']

        print(f"\n{i}. {status} {pocket['name'].upper()}")
        print(f"   {'─' * 90}")
        print(f"   📝 {pocket['description']}")
        print(f"   🎯 Target: {pocket['target_papers']} papers | Priority: {priority}")

        print(f"\n   📍 Focus areas:")
        for focus in pocket['focus']:
            print(f"      • {focus}")

        print(f"\n   🔍 Search queries:")
        for query in pocket['search_queries'][:2]:  # Show first 2
            print(f"      • \"{query}\"")
        if len(pocket['search_queries']) > 2:
            print(f"      ... + {len(pocket['search_queries'])-2} more queries")

        print(f"\n   📊 Key metrics: {', '.join(pocket['key_metrics'][:3])}...")
        print(f"   💡 Note: {pocket['notes']}")

    print("\n" + "=" * 100)
    print(f"📌 TOTAL TARGET: {config['general_targets']['total_papers_target']} papers")
    print(f"📌 PER POCKET: {config['general_targets']['papers_per_pocket']} papers")
    print("=" * 100 + "\n")

def print_pocket_detailed(config, pocket_id):
    """Print detailed info for one pocket"""
    pockets = config['pockets']
    if pocket_id not in pockets:
        print(f"❌ Pocket '{pocket_id}' not found")
        return

    pocket = pockets[pocket_id]

    print(f"\n{'=' * 100}")
    print(f"📖 POCKET DETALLADO: {pocket['name']}")
    print(f"{'=' * 100}")

    print(f"\n📝 DESCRIPCIÓN:")
    print(f"   {pocket['description']}\n")

    print(f"🎯 FOCUS AREAS:")
    for focus in pocket['focus']:
        print(f"   • {focus}")

    print(f"\n📊 KEY METRICS:")
    for metric in pocket['key_metrics']:
        print(f"   • {metric}")

    print(f"\n🔍 SEARCH QUERIES ({len(pocket['search_queries'])} total):")
    for i, query in enumerate(pocket['search_queries'], 1):
        print(f"   {i}. \"{query}\"")

    print(f"\n🏷️  EXAMPLE KEYWORDS:")
    keywords = pocket['examples_keywords']
    if isinstance(keywords, list):
        for kw in keywords:
            print(f"   • {kw}")
    else:
        print(f"   {keywords}")

    print(f"\n🎯 TARGET: {pocket['target_papers']} papers")
    print(f"⚡ PRIORITY: {pocket['priority']}")
    print(f"📌 STATUS: {pocket['status']}")
    print(f"\n💡 NOTES: {pocket['notes']}")
    print(f"\n{'=' * 100}\n")

def export_pocket_searches(config, output_file="data/pocket_searches.json"):
    """Export all searches organized by pocket"""
    searches = {}
    for pocket_id, pocket in config['pockets'].items():
        searches[pocket_id] = {
            "name": pocket['name'],
            "queries": pocket['search_queries'],
            "target_papers": pocket['target_papers'],
            "priority": pocket['priority']
        }

    with open(output_file, 'w') as f:
        json.dump(searches, f, indent=2)

    print(f"✅ Search queries exported to {output_file}")

if __name__ == '__main__':
    import sys

    config = load_pockets_config("pockets_config.yaml")

    if len(sys.argv) > 1:
        # Show specific pocket
        pocket_id = sys.argv[1]
        print_pocket_detailed(config, pocket_id)
    else:
        # Show summary
        print_pocket_summary(config)

    # Always export
    export_pocket_searches(config)
