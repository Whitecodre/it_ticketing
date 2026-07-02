import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tickets.models import Asset, AssetLog

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the asset database with realistic sample assets'

    def handle(self, *args, **options):
        # Get or create a default user to act as "actor" for logs
        actor = User.objects.filter(is_superuser=True).first()
        if not actor:
            actor = User.objects.first()
            if not actor:
                self.stdout.write(self.style.ERROR('No users found. Please create at least one user first.'))
                return

        users = User.objects.filter(is_active=True)
        if not users:
            self.stdout.write(self.style.WARNING('No active users found. Assets will be unassigned.'))

        # Sample data
        asset_data = [
            {
                'name': 'Dell Latitude 5420',
                'asset_type': 'LAPTOP',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'Latitude 5420',
                'manufacturer': 'Dell',
                'location': 'Building A, Floor 3, IT Dept',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Standard issue laptop for developers.'
            },
            {
                'name': 'HP EliteBook 840 G8',
                'asset_type': 'LAPTOP',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'EliteBook 840 G8',
                'manufacturer': 'HP',
                'location': 'Building B, Floor 2, Finance',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Finance team laptops.'
            },
            {
                'name': 'Apple MacBook Pro 16" M3',
                'asset_type': 'LAPTOP',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'MacBook Pro 16" M3',
                'manufacturer': 'Apple',
                'location': 'Building C, Design Studio',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Graphic design team.'
            },
            {
                'name': 'Lenovo ThinkPad X1 Carbon Gen 10',
                'asset_type': 'LAPTOP',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'ThinkPad X1 Carbon Gen 10',
                'manufacturer': 'Lenovo',
                'location': 'Building D, Executive Office',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'C-suite laptops.'
            },
            {
                'name': 'Dell PowerEdge R740',
                'asset_type': 'SERVER',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'PowerEdge R740',
                'manufacturer': 'Dell',
                'location': 'Data Center A, Rack 12',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Production application server.'
            },
            {
                'name': 'Cisco Catalyst 9300 Switch',
                'asset_type': 'NETWORK',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'Catalyst 9300',
                'manufacturer': 'Cisco',
                'location': 'Data Center A, Rack 5',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Core network switch.'
            },
            {
                'name': 'HP LaserJet Enterprise M607',
                'asset_type': 'PRINTER',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'LaserJet Enterprise M607',
                'manufacturer': 'HP',
                'location': 'Building A, Floor 2, Breakroom',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'High-volume printer for staff.'
            },
            {
                'name': 'Microsoft Office 365 E3 License',
                'asset_type': 'SOFTWARE',
                'serial_number': '',
                'model': 'Office 365 E3',
                'manufacturer': 'Microsoft',
                'location': 'Global',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': None,
                'status': 'ACTIVE',
                'notes': 'Enterprise license for all employees.'
            },
            {
                'name': 'Dell OptiPlex 7080 Desktop',
                'asset_type': 'COMPUTER',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'OptiPlex 7080',
                'manufacturer': 'Dell',
                'location': 'Building B, Floor 1, HR',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'HR department desktops.'
            },
            {
                'name': 'Apple iMac 24" M3',
                'asset_type': 'COMPUTER',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'iMac 24" M3',
                'manufacturer': 'Apple',
                'location': 'Building C, Marketing',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Marketing team all-in-ones.'
            },
            {
                'name': 'Lenovo ThinkStation P620',
                'asset_type': 'COMPUTER',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'ThinkStation P620',
                'manufacturer': 'Lenovo',
                'location': 'Data Center B, Lab 3',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Engineering workstations.'
            },
            {
                'name': 'Cisco Meraki MX68 Firewall',
                'asset_type': 'NETWORK',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'Meraki MX68',
                'manufacturer': 'Cisco',
                'location': 'Data Center A, Rack 2',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Edge firewall.'
            },
            {
                'name': 'Dell PowerStore 500T Storage',
                'asset_type': 'SERVER',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'PowerStore 500T',
                'manufacturer': 'Dell',
                'location': 'Data Center A, Rack 8',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'SAN storage for VMs.'
            },
            {
                'name': 'Epson WorkForce Pro WF-C5790',
                'asset_type': 'PRINTER',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'WorkForce Pro WF-C5790',
                'manufacturer': 'Epson',
                'location': 'Building D, Finance',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': date.today() + timedelta(days=random.randint(100, 500)),
                'status': 'ACTIVE',
                'notes': 'Color multifunction printer.'
            },
            {
                'name': 'Microsoft Windows Server 2022 License',
                'asset_type': 'SOFTWARE',
                'serial_number': '',
                'model': 'Windows Server 2022',
                'manufacturer': 'Microsoft',
                'location': 'Data Center A',
                'purchase_date': date.today() - timedelta(days=random.randint(30, 900)),
                'warranty_expiry': None,
                'status': 'ACTIVE',
                'notes': 'Server OS license for all hosts.'
            },
            # Some assets with different statuses for testing
            {
                'name': 'Dell Latitude 7400 (Damaged)',
                'asset_type': 'LAPTOP',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'Latitude 7400',
                'manufacturer': 'Dell',
                'location': 'IT Repair Shop',
                'purchase_date': date.today() - timedelta(days=500),
                'warranty_expiry': date.today() - timedelta(days=100),
                'status': 'DAMAGED',
                'notes': 'Screen cracked, pending scrap approval.'
            },
            {
                'name': 'HP ProBook 450 G7 (In Store)',
                'asset_type': 'LAPTOP',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'ProBook 450 G7',
                'manufacturer': 'HP',
                'location': 'IT Store Room',
                'purchase_date': date.today() - timedelta(days=300),
                'warranty_expiry': date.today() + timedelta(days=200),
                'status': 'IN_STORE',
                'notes': 'Spare laptop, ready for deployment.'
            },
            {
                'name': 'Apple Mac mini M2 (Maintenance)',
                'asset_type': 'COMPUTER',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'Mac mini M2',
                'manufacturer': 'Apple',
                'location': 'IT Workshop',
                'purchase_date': date.today() - timedelta(days=200),
                'warranty_expiry': date.today() + timedelta(days=300),
                'status': 'MAINTENANCE',
                'notes': 'Undergoing hardware upgrade.'
            },
            {
                'name': 'Lenovo ThinkPad X1 Yoga (Scrapped)',
                'asset_type': 'LAPTOP',
                'serial_number': f'SN-{random.randint(1000,9999)}',
                'model': 'ThinkPad X1 Yoga',
                'manufacturer': 'Lenovo',
                'location': 'IT Recycling',
                'purchase_date': date.today() - timedelta(days=800),
                'warranty_expiry': date.today() - timedelta(days=400),
                'status': 'SCRAPPED',
                'notes': 'Battery failure, uneconomical to repair.'
            },
        ]

        created_count = 0
        for data in asset_data:
            # Assign to a random user if available and status is ACTIVE
            if data['status'] == 'ACTIVE' and users:
                assigned_to = random.choice(users)
            else:
                assigned_to = None

            # Create asset
            asset = Asset.objects.create(
                name=data['name'],
                asset_type=data['asset_type'],
                serial_number=data['serial_number'],
                model=data['model'],
                manufacturer=data['manufacturer'],
                location=data['location'],
                purchase_date=data['purchase_date'],
                warranty_expiry=data['warranty_expiry'],
                status=data['status'],
                assigned_to=assigned_to,
                notes=data['notes'],
            )
            # tracking_id is auto-generated in save()

            # Create an initial log entry
            AssetLog.objects.create(
                asset=asset,
                action=AssetLog.Action.CREATED,
                actor=actor,
                details={'source': 'seed_assets', 'initial_status': data['status']}
            )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f'✅ Created asset: {asset.tracking_id} - {asset.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Done! {created_count} new assets created.'))