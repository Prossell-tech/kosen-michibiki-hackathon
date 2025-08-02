import asyncio
import serial

PAST_QZQSM_ENTRIES = [
    ("(試験/訓練) 2019年11月27日18時10分 和歌山県南方沖 M9.0",
     "$QZQSM,57,9AAF8DED25000325BA00DA4A0F5AAC5A8000000008000000200000136DCCFB4*02"),
    ("(発表) 2019年2月21日21時22分 胆振地方中東部 M5.8",
     "$QZQSM,57,9AAC89558B0003240000AB160F3A2499B40000000000002000000010C93712C*0F"),
    ("(発表) 2019年12月26日18時29分 宮城県沖 深さ50km M4.6",
     "$QZQSM,57,53AD16692E80035C0000D25A192E47C99E011B8000000000000000116D6E0A8*0D"),
    ("(発表) 2022年8月26日08時48分 天草灘 深さ10km M4.6",
     "$QZQSM,56,53AD1466FA00035C0000CDF0052EC408000104000000000000000000012D801724*05"),
    ("(訂正) 2019年11月15日01時18分 インドネシア付近 深さ不明 M7.1",
     "$QZQSM,56,53AD15BA49800351C5007412FFC7EE405E00FCC00000000000000012A54CEC8*7F"),
    ("(発表) 2019年10月12日18時23分 千葉県 震度4",
     "$QZQSM,56,53AD1D312B800312B2300000000000000000000000000000000000124DBF404*7F"),
    ("(発表) 2022年8月26日08時48分 鹿児島県 震度4",
     "$QZQSM,56,C6AD1C66F980066F82B80000000000000000000000000000000000129A6F7B8*72"),
    ("(試験/訓練) 大津波警報 2019年11月27日18時10分",
     "$QZQSM,57,9AAFADED200001E51A00524068480000000000000000000000000011C72342C*0F"),
    ("(発表) 津波警報 2022年1月16日 トンガ火山噴火",
     "$QZQSM,56,9AACA8BECF0001E8F67C37FF3348000000000000000000000000001316E6B24*04"),
    ("(解除) 津波警報 2022年1月16日 トンガ火山噴火",
     "$QZQSM,56,53ADA8BECF0001E8F67C27FF2C100000000000000000000000000012C1D36B4*74"),
]


async def read_serial_line(ser):
    raw = await asyncio.to_thread(ser.readline)
    try:
        return raw.decode(errors="ignore").rstrip("\r\n")
    except Exception:
        return raw.decode("utf-8", "ignore").rstrip("\r\n")


def open_serial(port: str, baudrate: int, timeout=None) -> serial.Serial:
    ser = serial.Serial(port, baudrate, timeout=timeout)
    print(f"[SERIAL] Opened port {port} at {baudrate} baud")
    return ser


def select_dummy_qzqsm() -> str:
    print("Select a dummy QZQSM message:")
    for idx, (label, _) in enumerate(PAST_QZQSM_ENTRIES, 1):
        print(f" {idx}. {label}")
    while True:
        choice = input(f"Enter number (1-{len(PAST_QZQSM_ENTRIES)}): ")
        if choice.isdigit():
            i = int(choice)
            if 1 <= i <= len(PAST_QZQSM_ENTRIES):
                selected_label, msg = PAST_QZQSM_ENTRIES[i-1]
                print(f"Selected: {selected_label}")
                return msg
        print("Invalid selection, try again.")
