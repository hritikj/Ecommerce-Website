CREATE DATABASE IF NOT EXISTS product_db;
USE product_db;

CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(180) NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  stock INT DEFAULT 0,
  image_url VARCHAR(500),
  category_id INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

INSERT INTO categories (name) VALUES ('Home Goods'), ('Apparel'), ('Kitchen'), ('Stationery')
  ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO products (name, description, price, stock, image_url, category_id) VALUES
('Linen Table Runner', 'Hand-loomed pure linen runner, stone-washed for softness.', 38.00, 42, 'https://images.unsplash.com/photo-1600166898405-da9535204843?w=600', 1),
('Ceramic Pour-Over Set', 'Matte glazed stoneware dripper with a solid oak stand.', 64.00, 20, 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=600', 3),
('Wool Field Jacket', 'Water-resistant wool-blend jacket cut for layering.', 168.00, 15, 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600', 2),
('Brass Desk Lamp', 'Solid brass articulating lamp with a linen shade.', 92.00, 25, 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600', 1),
('Bookbinder Notebook', 'Coptic-stitched notebook, 120 pages of cream cotton paper.', 22.00, 60, 'https://images.unsplash.com/photo-1517971071642-34a2d3ecc9cd?w=600', 4),
('Cast Iron Skillet', 'Pre-seasoned 10-inch skillet, forged in small batches.', 54.00, 30, 'https://images.unsplash.com/photo-1602273660127-a0000560e0c1?w=600', 3),
('Alpaca Throw Blanket', 'Undyed alpaca wool throw, woven on a shuttle loom.', 145.00, 18, 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600', 1),
('Selvedge Denim Apron', 'Cross-back apron in 12oz selvedge denim.', 58.00, 22, 'https://images.unsplash.com/photo-1621293954908-907159247fc8?w=600', 2)
ON DUPLICATE KEY UPDATE name = VALUES(name);
