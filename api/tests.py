from django.test import TestCase, Client
from django.urls import reverse
from api.models import Participant, Receipt, ReceiptInfo, Settlement
from io import BytesIO
from openpyxl import load_workbook

class ExportExcelTest(TestCase):
    def setUp(self):
        self.p1 = Participant.objects.create(name="최희수")
        self.p2 = Participant.objects.create(name="하승연")

        self.receipt = Receipt.objects.create(
            file_name="test.jpg",
            image_path="receipts/test.jpg"
        )
        ReceiptInfo.objects.create(receipt=self.receipt, store_name="상호1", item_name="김밥", quantity=1, unit_price=3000, total_amount=3000)
        ReceiptInfo.objects.create(receipt=self.receipt, store_name="상호1", item_name="라면", quantity=1, unit_price=4000, total_amount=4000)

        self.settlement = Settlement.objects.create(
            result={"최희수": 3000, "하승연": 4000},
            method="item"
        )
        self.settlement.receipts.set([self.receipt])
        self.settlement.participants.set([self.p1, self.p2])

    def test_export_excel_save_file(self):
        client = Client()
        url = reverse("api:export_settlement_excel", kwargs={"settlement_id": self.settlement.id})
        response = client.get(url)

        self.assertEqual(response.status_code, 200)

        with open("test_output.xlsx", "wb") as f:
            f.write(response.content)
