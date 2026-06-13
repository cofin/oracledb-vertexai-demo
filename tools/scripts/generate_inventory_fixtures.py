"""Script to generate realistic inventory fixtures for Cymbal Coffee."""

import argparse
import gzip
import json
from pathlib import Path
import random
from typing import Any

def generate_inventory(output_file: Path | None = None) -> None:
    """Generate inventory data based on existing store and product fixtures.
    
    This function reads the store and product fixtures, generates random inventory
    records for a random subset of products in each store, and saves the result
    to a gzipped JSON file.
    """
    root_dir = Path(__file__).resolve().parents[2]
    fixtures_dir = root_dir / "src" / "app" / "db" / "fixtures"
    
    store_file = fixtures_dir / "store.json.gz"
    product_file = fixtures_dir / "product.json.gz"
    
    if output_file is None:
        output_file = fixtures_dir / "store_product_inventory.json.gz"
        
    with gzip.open(store_file, "rb") as f:
        stores = json.load(f)
        
    with gzip.open(product_file, "rb") as f:
        products = json.load(f)
        
    inventory: list[dict[str, Any]] = []
    current_id = 1
    
    for store in stores:
        store_id = store["id"]
        # Limit to 5 products per store to keep file size small
        num_products = min(5, len(products))
        selected_products = random.sample(products, num_products)
        
        for product in selected_products:
            product_id = product["id"]
            quantity = random.randint(0, 50)
            
            if quantity == 0:
                status = "OUT_OF_STOCK"
            elif quantity < 10:
                status = "LOW_STOCK"
            else:
                status = "IN_STOCK"
                
            pickup = random.choice([True, False])
            
            inventory.append({
                "id": current_id,
                "store_id": store_id,
                "product_id": product_id,
                "quantity_available": quantity,
                "stock_status": status,
                "pickup_available": pickup
            })
            current_id += 1
            
    if output_file.suffix == ".gz":
        with gzip.open(output_file, "wt", encoding="utf-8") as f:
            json.dump(inventory, f, indent=2)
    else:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(inventory, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate inventory fixtures.")
    parser.add_argument("--output", type=str, help="Path to output file")
    args = parser.parse_args()
    
    out_path = Path(args.output) if args.output else None
    generate_inventory(output_file=out_path)
