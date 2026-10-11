from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Build, Product, User


def _is_empty(db: Session, model) -> bool:
    return (db.scalar(select(func.count()).select_from(model)) or 0) == 0

# Datos iniciales tomados literalmente de la sección "Hardware" del index.html
# original, para que el catálogo público no cambie visualmente al pasar a
# base de datos. El precio y el stock no existían antes (la landing era
# estática) y se agregan como punto de partida editable desde el panel admin.
INITIAL_PRODUCTS = [
    dict(
        name="AMD Ryzen 9",
        brand="AMD",
        description="Máximo rendimiento multihilo. Ideal para gaming y workstations.",
        image_url="https://images.pexels.com/photos/30083229/pexels-photo-30083229.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=549.99,
        stock=18,
    ),
    dict(
        name="Intel Core i9",
        brand="Intel",
        description="Potencia y estabilidad para las cargas de trabajo más exigentes.",
        image_url="https://images.pexels.com/photos/785418/pexels-photo-785418.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=589.99,
        stock=14,
    ),
    dict(
        name="NVIDIA RTX 4080",
        brand="NVIDIA",
        description="Ray tracing y DLSS de última generación para gaming en 4K.",
        image_url="https://images.pexels.com/photos/8622911/pexels-photo-8622911.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=1199.99,
        stock=7,
    ),
    dict(
        name="AMD Radeon RX 7900",
        brand="AMD",
        description="Alternativa premium con rendimiento excepcional en cualquier resolución.",
        image_url="https://images.pexels.com/photos/8622911/pexels-photo-8622911.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=899.99,
        stock=0,
    ),
    dict(
        name="RAM DDR5 RGB",
        brand="DDR5",
        description="Alta frecuencia y latencias bajas. Iluminación RGB sincronizable.",
        image_url="https://images.pexels.com/photos/34006659/pexels-photo-34006659.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=189.99,
        stock=32,
    ),
    dict(
        name="SSD NVMe PCIe 5.0",
        brand="NVMe",
        description="Velocidades de hasta 12,000 MB/s. Cargas instantáneas garantizadas.",
        image_url="https://images.pexels.com/photos/2582937/pexels-photo-2582937.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=229.99,
        stock=25,
    ),
    dict(
        name="Placa Base Gaming",
        brand="Motherboard",
        description="Máxima compatibilidad de VRM robustos y conectividad moderna.",
        image_url="https://images.pexels.com/photos/2582937/pexels-photo-2582937.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=329.99,
        stock=11,
    ),
    dict(
        name="Fuente Modular 80+ Gold",
        brand="PSU",
        description="Eficiencia energética premium. Cables modulares para build limpio.",
        image_url="https://images.pexels.com/photos/33693785/pexels-photo-33693785.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=139.99,
        stock=20,
    ),
    dict(
        name="Gabinete Gamer ATX",
        brand="Case",
        description="Panel de cristal templado, flujo de aire optimizado y gestión de cables.",
        image_url="https://images.pexels.com/photos/1038916/pexels-photo-1038916.jpeg?auto=compress&cs=tinysrgb&w=500",
        price=99.99,
        stock=16,
    ),
]


def seed_products_if_empty(db: Session) -> None:
    if _is_empty(db, Product):
        for data in INITIAL_PRODUCTS:
            db.add(Product(**data))
        db.commit()


# Datos tomados literalmente de la sección "Gaming" del index.html original.
INITIAL_BUILDS = [
    dict(
        tier="Inicial",
        tier_emoji="🎮",
        name="Gamer Inicial",
        budget_label="$500 – $800 USD",
        cpu="AMD Ryzen 5 5600 / Intel i5-12400F",
        gpu="NVIDIA RTX 3060 / RX 6650 XT",
        ram="16 GB DDR4 3200 MHz",
        storage="500 GB NVMe",
        performance_note="1080p / 60–100 fps en AAA",
        performance_pct=45,
        image_url="https://images.pexels.com/photos/8607559/pexels-photo-8607559.jpeg?auto=compress&cs=tinysrgb&w=700",
        featured=False,
    ),
    dict(
        tier="Intermedio",
        tier_emoji="💜",
        name="Gamer Intermedio",
        budget_label="$800 – $1,500 USD",
        cpu="AMD Ryzen 7 7700X / Intel i7-13700K",
        gpu="NVIDIA RTX 4070 / RX 7800 XT",
        ram="32 GB DDR5 5200 MHz",
        storage="1 TB NVMe PCIe 4.0",
        performance_note="1440p / 100–165 fps en AAA",
        performance_pct=72,
        image_url="https://images.pexels.com/photos/30469967/pexels-photo-30469967.jpeg?auto=compress&cs=tinysrgb&w=700",
        featured=True,
    ),
    dict(
        tier="Profesional",
        tier_emoji="🚀",
        name="Gamer Profesional",
        budget_label="$1,500 – $3,000+ USD",
        cpu="AMD Ryzen 9 7950X / Intel i9-14900K",
        gpu="NVIDIA RTX 4090 / RX 7900 XTX",
        ram="64 GB DDR5 6000 MHz",
        storage="2 TB NVMe PCIe 5.0",
        performance_note="4K / 144+ fps con ray tracing",
        performance_pct=98,
        image_url="https://images.pexels.com/photos/32260117/pexels-photo-32260117.jpeg?auto=compress&cs=tinysrgb&w=700",
        featured=False,
    ),
]


def seed_builds_if_empty(db: Session) -> None:
    if _is_empty(db, Build):
        for data in INITIAL_BUILDS:
            db.add(Build(**data))
        db.commit()


def seed_admin_if_missing(db: Session, email, password, name="Administrador") -> None:
    existing = db.scalars(select(User).where(User.email == email)).first()
    if existing is None:
        admin = User(name=name, email=email, role="admin", active=True, email_verified=True)
        admin.set_password(password)
        db.add(admin)
        db.commit()
