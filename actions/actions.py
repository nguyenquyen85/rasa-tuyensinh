import json
import re
import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from fuzzywuzzy import process, fuzz

# Biến toàn cục lưu đường dẫn đến file nganh.json
NGANH_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nganh.json")

def load_nganh_data():
    """
    Hàm đọc dữ liệu từ file nganh.json
    
    Returns:
        list: Danh sách các ngành học
    """
    try:
        with open(NGANH_JSON_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Lỗi khi đọc file JSON: {e}")
        return []

def find_similar_nganh(nganh_name, nganh_list, threshold=70):
    """
    Tìm kiếm ngành gần đúng sử dụng fuzzywuzzy
    
    Args:
        nganh_name (str): Tên ngành cần tìm
        nganh_list (list): Danh sách các ngành
        threshold (int): Ngưỡng điểm tương đồng (mặc định: 70)
        
    Returns:
        dict: Ngành học tương đồng nhất nếu điểm cao hơn ngưỡng, None nếu không tìm thấy
    """
    if not nganh_name or not nganh_list:
        return None
        
    # Trích xuất tên ngành từ danh sách
    nganh_names = [nganh["ten_nganh"] for nganh in nganh_list]
    
    # Tìm tên ngành tương đồng nhất
    best_match, score = process.extractOne(nganh_name, nganh_names, scorer=fuzz.token_sort_ratio)
    
    if score >= threshold:
        # Trả về đối tượng ngành đầy đủ
        for nganh in nganh_list:
            if nganh["ten_nganh"] == best_match:
                return nganh
                
    return None

class ActionXuLyTen(Action):
    """
    Hành động xử lý tên người dùng
    """
    def name(self) -> Text:
        return "action_xu_ly_ten"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Lấy tên người dùng từ slot
        ten_nguoi_dung = tracker.get_slot("ten_nguoi_dung")
        
        if not ten_nguoi_dung:
            dispatcher.utter_message(text="Tôi chưa biết tên bạn. Bạn có thể cho tôi biết tên được không?")
            return []
            
        # Xử lý tên người dùng bằng regex
        processed_name = self.process_name(ten_nguoi_dung)
        
        # Gửi lời chào với tên đã xử lý
        dispatcher.utter_message(response="utter_chao_sau_khi_biet_ten", ten_nguoi_dung=processed_name)
        
        return [SlotSet("ten_nguoi_dung", processed_name)]
    
    def process_name(self, name: Text) -> Text:
        """
        Xử lý tên người dùng:
        - Loại bỏ khoảng trắng thừa
        - Chuẩn hóa các chữ cái đầu thành chữ hoa
        - Loại bỏ các ký tự đặc biệt
        
        Args:
            name (str): Tên người dùng cần xử lý
            
        Returns:
            str: Tên đã được xử lý
        """
        if not name:
            return ""
            
        # Loại bỏ ký tự đặc biệt và số
        name = re.sub(r'[^a-zA-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯĂẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼỀỀỂưăạảấầẩẫậắằẳẵặẹẻẽềềểỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪễếệỉịọỏốồổỗộớờởỡợụủứừỬỮỰỲỴÝỶỸửữựỳỵỷỹ\s]', '', name)
        
        # Loại bỏ khoảng trắng thừa
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Chuẩn hóa chữ cái đầu thành chữ hoa
        name = name.title()
        
        return name

class ActionTraLoiNganhTuyenSinh(Action):
    """
    Hành động trả lời về các ngành tuyển sinh
    """
    def name(self) -> Text:
        return "action_tra_loi_nganh_tuyen_sinh"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Đọc danh sách ngành từ JSON
        nganh_list = load_nganh_data()
        
        if not nganh_list:
            dispatcher.utter_message(text="Hiện tại tôi không thể cung cấp thông tin về các ngành tuyển sinh. Xin vui lòng thử lại sau.")
            return []
            
        # Tạo thông báo về các ngành
        message = "Trường Đại học Giao thông Vận tải TP.HCM đào tạo các ngành sau:\n"
        for i, nganh in enumerate(nganh_list, 1):
            message += f"{i}. {nganh['ten_nganh']}\n"
            
        dispatcher.utter_message(text=message)
        return []

class ActionTraLoiThongTinNganh(Action):
    """
    Hành động trả lời thông tin giới thiệu về ngành
    """
    def name(self) -> Text:
        return "action_tra_loi_thong_tin_nganh"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ten_nganh = tracker.get_slot("ten_nganh")
        if not ten_nganh:
            dispatcher.utter_message(text="Bạn muốn tìm hiểu về ngành nào?")
            return []
            
        nganh_list = load_nganh_data()
        nganh = find_similar_nganh(ten_nganh, nganh_list)
        
        if nganh:
            message = f"Dưới đây là thông tin về ngành {nganh['ten_nganh']}, mã ngành {nganh['ma_nganh']}:\n\n"
            message += nganh["gioi_thieu_chung"]
            dispatcher.utter_message(text=message)
            return [SlotSet("ten_nganh", nganh["ten_nganh"])]
        else:
            dispatcher.utter_message(text=f"Tôi không tìm thấy thông tin về ngành '{ten_nganh}'. Bạn có thể kiểm tra lại tên ngành hoặc tìm hiểu về ngành khác.")
            return []

class ActionTraLoiCoHoiViecLam(Action):
    """
    Hành động trả lời về cơ hội việc làm của ngành
    """
    def name(self) -> Text:
        return "action_tra_loi_co_hoi_viec_lam"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ten_nganh = tracker.get_slot("ten_nganh")
        if not ten_nganh:
            dispatcher.utter_message(text="Bạn muốn tìm hiểu cơ hội việc làm của ngành nào?")
            return []
            
        nganh_list = load_nganh_data()
        nganh = find_similar_nganh(ten_nganh, nganh_list)
        
        if nganh:
            message = f"Cơ hội việc làm của ngành {nganh['ten_nganh']}:\n\n"
            for i, co_hoi in enumerate(nganh["co_hoi_viec_lam"], 1):
                message += f"{i}. {co_hoi}\n"
                
            dispatcher.utter_message(text=message)
            return [SlotSet("ten_nganh", nganh["ten_nganh"])]
        else:
            dispatcher.utter_message(text=f"Tôi không tìm thấy thông tin về cơ hội việc làm của ngành '{ten_nganh}'. Bạn có thể kiểm tra lại tên ngành hoặc tìm hiểu về ngành khác.")
            return []

class ActionTraLoiDiemChuanNganh(Action):
    """
    Hành động trả lời về điểm chuẩn của ngành
    """
    def name(self) -> Text:
        return "action_tra_loi_diem_chuan_nganh"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ten_nganh = tracker.get_slot("ten_nganh")
        nam = tracker.get_slot("nam")
        
        if not ten_nganh:
            dispatcher.utter_message(text="Bạn muốn tìm hiểu điểm chuẩn của ngành nào?")
            return []
            
        nganh_list = load_nganh_data()
        nganh = find_similar_nganh(ten_nganh, nganh_list)
        
        if not nganh:
            dispatcher.utter_message(text=f"Tôi không tìm thấy thông tin về ngành '{ten_nganh}'. Bạn có thể kiểm tra lại tên ngành hoặc tìm hiểu về ngành khác.")
            return []
            
        # Xử lý năm cụ thể nếu có
        if nam:
            # Trích xuất năm từ chuỗi (ví dụ: "năm 2024" -> "2024")
            nam_match = re.search(r'\d{4}', nam)
            if nam_match:
                nam_value = nam_match.group(0)
                if nam_value in nganh["diem_chuan"]:
                    diem = nganh["diem_chuan"][nam_value]
                    if diem is not None:
                        dispatcher.utter_message(text=f"Điểm chuẩn ngành {nganh['ten_nganh']} năm {nam_value} là: {diem} điểm.")
                    else:
                        dispatcher.utter_message(text=f"Chưa có thông tin điểm chuẩn ngành {nganh['ten_nganh']} năm {nam_value}.")
                else:
                    dispatcher.utter_message(text=f"Tôi không có thông tin về điểm chuẩn ngành {nganh['ten_nganh']} năm {nam_value}.")
            else:
                # Trường hợp người dùng nhập "năm ngoái", "năm trước", v.v.
                self.tra_loi_diem_chuan_khong_co_nam(dispatcher, nganh)
        else:
            # Trường hợp không có năm cụ thể
            self.tra_loi_diem_chuan_khong_co_nam(dispatcher, nganh)
            
        return [SlotSet("ten_nganh", nganh["ten_nganh"])]
        
    def tra_loi_diem_chuan_khong_co_nam(self, dispatcher, nganh):
        """
        Trả lời điểm chuẩn khi không có năm cụ thể
        """
        message = f"Điểm chuẩn ngành {nganh['ten_nganh']} các năm gần đây:\n\n"
        for nam, diem in nganh["diem_chuan"].items():
            if diem is not None:
                message += f"Năm {nam}: {diem} điểm\n"
                
        dispatcher.utter_message(text=message)

class ActionTraLoiKhoiXetTuyen(Action):
    """
    Hành động trả lời về khối xét tuyển của ngành
    """
    def name(self) -> Text:
        return "action_tra_loi_khoi_xet_tuyen"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ten_nganh = tracker.get_slot("ten_nganh")
        if not ten_nganh:
            dispatcher.utter_message(text="Bạn muốn tìm hiểu khối xét tuyển của ngành nào?")
            return []
            
        nganh_list = load_nganh_data()
        nganh = find_similar_nganh(ten_nganh, nganh_list)
        
        if nganh:
            message = f"Khối xét tuyển của ngành {nganh['ten_nganh']} là: "
            message += ", ".join(nganh["khoi_xet_tuyen"])
            
            dispatcher.utter_message(text=message)
            return [SlotSet("ten_nganh", nganh["ten_nganh"])]
        else:
            dispatcher.utter_message(text=f"Tôi không tìm thấy thông tin về khối xét tuyển của ngành '{ten_nganh}'. Bạn có thể kiểm tra lại tên ngành hoặc tìm hiểu về ngành khác.")
            return []