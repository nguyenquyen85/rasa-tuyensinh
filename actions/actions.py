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

def find_similar_nganh(nganh_name, nganh_list, threshold=60):
    """
    Tìm kiếm ngành gần đúng sử dụng fuzzywuzzy với cải tiến nhận dạng từ viết tắt
    
    Args:
        nganh_name (str): Tên ngành cần tìm
        nganh_list (list): Danh sách các ngành
        threshold (int): Ngưỡng điểm tương đồng (mặc định: 60)
        
    Returns:
        dict: Ngành học tương đồng nhất nếu điểm cao hơn ngưỡng, None nếu không tìm thấy
    """
    if not nganh_name or not nganh_list:
        return None
    
    # Tiền xử lý tên ngành cần tìm
    nganh_name = nganh_name.lower().strip()
    
    # Ánh xạ từ viết tắt sang tên đầy đủ
    viet_tat_mapping = {
        # Các từ viết tắt chung
        "cntt": "công nghệ thông tin",
        "ktpm": "kỹ thuật phần mềm",
        "httt": "hệ thống thông tin",
        "attt": "an toàn thông tin",
        "ktmt": "kỹ thuật máy tính",
        "khmt": "khoa học máy tính",
        "kt": "kỹ thuật",
        "cn": "công nghệ",
        "oto": "ô tô",
        "dc": "động cơ",
        "dt": "điện tử",
        "dtvt": "điện tử viễn thông",
        "tdhvđk": "tự động hóa và điều khiển",
        "tdh": "tự động hóa",
        "ck": "cơ khí",
        "cdt": "cơ điện tử",
        "ctm": "chế tạo máy",
        "xd": "xây dựng",
        "ktxd": "kỹ thuật xây dựng",
        "cdgt": "công trình giao thông",
        "gt": "giao thông",
        "vt": "vận tải",
        "log": "logistics",
        "qtkd": "quản trị kinh doanh",
        "qtdn": "quản trị doanh nghiệp",
        "mkt": "marketing",
        "tmdt": "thương mại điện tử",
        "qtns": "quản trị nhân sự",
        "qtnl": "quản trị nhân lực",
        "qldt": "quản lý đô thị",
        "tckt": "tài chính kế toán",
        "tc": "tài chính",
        "kt": "kế toán"
    }
    
    # Xử lý viết tắt: kiểm tra xem nganh_name có phải là viết tắt không
    for viet_tat, ten_day_du in viet_tat_mapping.items():
        if viet_tat in nganh_name:
            nganh_name = nganh_name.replace(viet_tat, ten_day_du)
    
    # Tạo từ điển ánh xạ từ tên ngành viết thường sang ngành gốc
    nganh_mapping = {nganh["ten_nganh"].lower(): nganh for nganh in nganh_list}
    
    # Kiểm tra trùng khớp trực tiếp
    if nganh_name in nganh_mapping:
        return nganh_mapping[nganh_name]
    
    # Tìm kiếm bằng từng phần
    for ten_nganh, nganh in nganh_mapping.items():
        if nganh_name in ten_nganh or ten_nganh in nganh_name:
            return nganh
    
    # Tìm kiếm dựa trên các từ khóa chính
    keywords = nganh_name.split()
    if len(keywords) >= 2:  # Nếu có ít nhất 2 từ khóa
        for ten_nganh, nganh in nganh_mapping.items():
            # Kiểm tra xem có ít nhất 2 từ khóa có trong tên ngành không
            count_matches = sum(1 for keyword in keywords if keyword in ten_nganh)
            if count_matches >= 2:
                return nganh
    
    # Sử dụng fuzzywuzzy để tìm kiếm tương đồng nếu các phương pháp trên không tìm thấy
    # Trích xuất tên ngành từ danh sách
    nganh_names = list(nganh_mapping.keys())
    
    # Thêm xử lý cho từng khúc của tên ngành để tăng độ chính xác
    best_score = 0
    best_match = None
    
    # Tìm với toàn bộ tên ngành
    for ten_nganh in nganh_names:
        # Sử dụng token_sort_ratio để so sánh không phụ thuộc vào thứ tự từ
        score = fuzz.token_sort_ratio(nganh_name, ten_nganh)
        # Sử dụng partial_ratio để bắt trường hợp tên ngành là một phần của ngành đầy đủ
        partial_score = fuzz.partial_ratio(nganh_name, ten_nganh)
        # Lấy điểm cao nhất giữa hai phương pháp
        final_score = max(score, partial_score)
        
        if final_score > best_score:
            best_score = final_score
            best_match = ten_nganh
    
    if best_score >= threshold:
        return nganh_mapping[best_match]
    

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
            message += f"\n{i}. {nganh['ten_nganh']}\n\n"
            
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
        
        # Biến để theo dõi xem có cần xóa slot nam không
        should_reset_nam = False
            
        # Xử lý năm cụ thể nếu có
        if nam:
            # Lấy năm hiện tại
            current_year = 2024  # Cập nhật theo năm hiện tại của hệ thống
            
            # Trích xuất năm từ chuỗi (ví dụ: "năm 2024" -> "2024")
            nam_match = re.search(r'\d{4}', nam)
            
            # Xử lý trường hợp "năm ngoái", "năm trước", "1 năm trước", "2 năm trước"
            if nam_match:
                # Trường hợp có số năm cụ thể
                nam_value = nam_match.group(0)
                should_reset_nam = True
                self.tra_loi_diem_chuan_nam_cu_the(dispatcher, nganh, nam_value)
            else:
                # Xử lý các cụm từ "năm ngoái", "năm trước", v.v.
                nam_value = self.xu_ly_nam_mo_ta(nam, current_year)
                if nam_value:
                    should_reset_nam = True
                    self.tra_loi_diem_chuan_nam_cu_the(dispatcher, nganh, str(nam_value))
                else:
                    self.tra_loi_diem_chuan_khong_co_nam(dispatcher, nganh)
        else:
            # Trường hợp không có năm cụ thể
            self.tra_loi_diem_chuan_khong_co_nam(dispatcher, nganh)
        
        # Danh sách các events cần trả về
        events = [SlotSet("ten_nganh", nganh["ten_nganh"])]
        
        # Nếu đã xử lý năm cụ thể, reset slot nam
        if should_reset_nam:
            events.append(SlotSet("nam", None))
            
        return events
    
    def xu_ly_nam_mo_ta(self, nam_mo_ta, current_year):
        """
        Xử lý các cụm từ miêu tả năm như "năm ngoái", "năm trước", "1 năm trước"
        
        Args:
            nam_mo_ta (str): Chuỗi miêu tả năm
            current_year (int): Năm hiện tại
            
        Returns:
            int: Năm cụ thể sau khi xử lý, None nếu không xác định được
        """
        nam_mo_ta = nam_mo_ta.lower()
        
        # Xử lý "năm ngoái", "năm trước"
        if re.search(r'năm\s+(ngoái|trước|vừa\s+rồi|vừa\s+qua)', nam_mo_ta):
            return current_year - 1
        
        # Xử lý "2 năm trước", "3 năm trước", etc.
        so_nam_match = re.search(r'(\d+)\s+năm\s+trước', nam_mo_ta)
        if so_nam_match:
            so_nam = int(so_nam_match.group(1))
            return current_year - so_nam
            
        # Xử lý "năm kia" (2 năm trước)
        if re.search(r'năm\s+kia', nam_mo_ta):
            return current_year - 2
            
        # Xử lý "năm nay"
        if re.search(r'năm\s+nay', nam_mo_ta):
            return current_year
        
        return None
        
    def tra_loi_diem_chuan_nam_cu_the(self, dispatcher, nganh, nam_value):
        """
        Trả lời điểm chuẩn cho một năm cụ thể
        
        Args:
            dispatcher: Rasa dispatcher
            nganh (dict): Thông tin về ngành
            nam_value (str): Năm cần tra cứu
        """
        if nam_value in nganh["diem_chuan"] and nganh["diem_chuan"][nam_value] is not None:
            diem = nganh["diem_chuan"][nam_value]
            dispatcher.utter_message(text=f"Điểm chuẩn ngành {nganh['ten_nganh']} năm {nam_value} là: {diem} điểm.")
        else:
            # Kiểm tra xem năm có trong danh sách các năm không
            nam_list = list(nganh["diem_chuan"].keys())
            if nam_value not in nam_list:
                # Nếu không có thông tin năm này, tìm năm gần nhất
                nam_gan_nhat = self.tim_nam_gan_nhat(nam_value, nam_list)
                if nam_gan_nhat:
                    diem = nganh["diem_chuan"][nam_gan_nhat]
                    dispatcher.utter_message(text=f"Không có thông tin điểm chuẩn ngành {nganh['ten_nganh']} năm {nam_value}. Nhưng tôi có thể cung cấp điểm chuẩn năm {nam_gan_nhat} là: {diem} điểm.")
                else:
                    dispatcher.utter_message(text=f"Chưa có thông tin điểm chuẩn ngành {nganh['ten_nganh']} năm {nam_value}.")
            else:
                dispatcher.utter_message(text=f"Chưa có thông tin điểm chuẩn ngành {nganh['ten_nganh']} năm {nam_value}.")
                
    def tim_nam_gan_nhat(self, nam_value, nam_list):
        """
        Tìm năm gần nhất với năm được yêu cầu trong danh sách các năm có sẵn
        
        Args:
            nam_value (str): Năm cần tìm
            nam_list (list): Danh sách các năm có sẵn
            
        Returns:
            str: Năm gần nhất, None nếu không tìm thấy
        """
        try:
            # Chuyển đổi sang số nguyên để so sánh
            target_year = int(nam_value)
            year_list = [int(year) for year in nam_list]
            
            # Sắp xếp các năm dựa trên khoảng cách với năm cần tìm
            closest_years = sorted(year_list, key=lambda x: abs(x - target_year))
            
            if closest_years:
                return str(closest_years[0])
                
        except (ValueError, TypeError):
            pass
            
        return None
        
    def tra_loi_diem_chuan_khong_co_nam(self, dispatcher, nganh):
        """
        Trả lời điểm chuẩn khi không có năm cụ thể
        """
        # Kiểm tra xem có thông tin điểm chuẩn không
        if not nganh["diem_chuan"]:
            dispatcher.utter_message(text=f"Hiện tại chưa có thông tin về điểm chuẩn ngành {nganh['ten_nganh']}.")
            return
            
        message = f"Điểm chuẩn ngành {nganh['ten_nganh']} các năm gần đây:\n\n"
        
        # Sắp xếp các năm từ mới nhất đến cũ nhất
        sorted_years = sorted([int(year) for year in nganh["diem_chuan"].keys()], reverse=True)
        
        for year in sorted_years:
            year_str = str(year)
            diem = nganh["diem_chuan"][year_str]
            if diem is not None:
                message += f"Năm {year_str}: {diem} điểm\n"
                
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
        
# Thêm các hàm tư vấn ngành theo điểm và sở thích
class ActionTuVanNganhTheoDiem(Action):
    """
    Hành động tư vấn ngành học dựa trên điểm thi của thí sinh
    """
    def name(self) -> Text:
        return "action_tu_van_nganh_theo_diem"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Trích xuất thông tin điểm từ tin nhắn của người dùng
        message = tracker.latest_message.get('text', '')
        diem_pattern = r'(\d{1,2}(\.\d+)?)\s*(?:điểm|diem)'
        diem_matches = re.findall(diem_pattern, message)
        
        diem = None
        if diem_matches:
            try:
                diem = float(diem_matches[0][0])
            except (ValueError, IndexError):
                pass
        
        if not diem:
            # Tìm số điểm từ các cụm từ thông thường
            diem_pattern = r'(\d{1,2}(\.\d+)?)'
            diem_matches = re.findall(diem_pattern, message)
            
            if diem_matches:
                try:
                    # Lấy số điểm đầu tiên tìm thấy
                    diem = float(diem_matches[0][0])
                except (ValueError, IndexError):
                    pass
        
        if not diem:
            dispatcher.utter_message(text="Xin lỗi, tôi không xác định được điểm của bạn. Vui lòng cho biết tổng điểm 3 môn là bao nhiêu?")
            return []
        
        # Đọc danh sách ngành từ JSON
        nganh_list = load_nganh_data()
        
        if not nganh_list:
            dispatcher.utter_message(text="Hiện tại tôi không thể cung cấp thông tin về các ngành tuyển sinh. Xin vui lòng thử lại sau.")
            return []
        
        # Tư vấn dựa theo mức điểm
        suitable_nganh = []
        
        # Lấy điểm chuẩn các ngành năm gần nhất
        latest_year = "2024"  # Năm mới nhất trong dữ liệu
        
        for nganh in nganh_list:
            if latest_year in nganh["diem_chuan"] and nganh["diem_chuan"][latest_year] is not None:
                diem_chuan = nganh["diem_chuan"][latest_year]
                chenh_lech = diem - diem_chuan
                
                # Chỉ xét các ngành có điểm chênh lệch từ -2 trở lên
                if chenh_lech >= -2:
                    # Thêm thông tin về khối xét tuyển
                    khoi_xet_tuyen = nganh["khoi_xet_tuyen"][0] if nganh["khoi_xet_tuyen"] else "N/A"
                    
                    suitable_nganh.append({
                        "ten_nganh": nganh["ten_nganh"],
                        "ma_khoi": khoi_xet_tuyen,
                        "diem_dat": diem,
                        "diem_chuan": diem_chuan,
                        "chenh_lech": chenh_lech
                    })
        
        # Sắp xếp theo chênh lệch điểm từ cao xuống thấp
        suitable_nganh.sort(key=lambda x: (-x["chenh_lech"], x["ten_nganh"]))
        
        if suitable_nganh:
            message = f"Với tổng điểm {diem:.1f}, dựa vào điểm chuẩn năm 2024, tôi tư vấn cho bạn các ngành sau:\n\n"
            
            for i, nganh in enumerate(suitable_nganh[:26], 1):  # Giới hạn 26 ngành
                message += f"{i}. {nganh['ten_nganh']} - Khối {nganh['ma_khoi']}\n"
                
                # Format theo trạng thái chênh lệch điểm
                if nganh["chenh_lech"] >= 0:
                    message += f"   Điểm của bạn: {nganh['diem_dat']:.1f}, Điểm chuẩn: {nganh['diem_chuan']:.1f} (Chênh lệch: +{nganh['chenh_lech']:.1f})\n\n"
                else:
                    message += f"   Điểm của bạn: {nganh['diem_dat']:.1f}, Điểm chuẩn: {nganh['diem_chuan']:.1f} (Chênh lệch: {nganh['chenh_lech']:.1f}) - cân nhắc phương thức xét tuyển khác\n\n"
                
            message += "Bạn có muốn biết thêm thông tin về ngành nào trong số này không?"
        else:
            message = f"Với mức điểm {diem:.1f}, bạn chưa đạt đủ điểm chuẩn các ngành của trường. Bạn có thể cân nhắc các phương thức xét tuyển khác như xét học bạ hoặc đánh giá năng lực."
        
        dispatcher.utter_message(text=message)
        return []

class ActionTuVanNganhTheoSoThich(Action):
    """
    Hành động tư vấn ngành học dựa trên sở thích của thí sinh
    """
    def name(self) -> Text:
        return "action_tu_van_nganh_theo_so_thich"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Lấy tin nhắn chứa sở thích của người dùng
        message = tracker.latest_message.get('text', '').lower()
        
        # Từ khóa ánh xạ sở thích với ngành học
        so_thich_nganh_mapping = {
            "máy tính": ["Công nghệ thông tin", "Kỹ thuật phần mềm", "Hệ thống thông tin", "An toàn thông tin"],
            "lập trình": ["Công nghệ thông tin", "Kỹ thuật phần mềm", "Khoa học máy tính"],
            "thiết kế": ["Kiến trúc", "Kỹ thuật công trình", "Thiết kế công nghiệp"],
            "ô tô": ["Công nghệ kỹ thuật ô tô", "Kỹ thuật cơ khí động lực"],
            "xe máy": ["Công nghệ kỹ thuật ô tô", "Kỹ thuật cơ khí động lực"],
            "động cơ": ["Công nghệ kỹ thuật ô tô", "Kỹ thuật cơ khí động lực"],
            "điện": ["Công nghệ kỹ thuật điện, điện tử", "Công nghệ kỹ thuật điều khiển và tự động hóa"],
            "điện tử": ["Công nghệ kỹ thuật điện, điện tử", "Công nghệ kỹ thuật điều khiển và tự động hóa"],
            "tự động hóa": ["Công nghệ kỹ thuật điều khiển và tự động hóa"],
            "robot": ["Công nghệ kỹ thuật điều khiển và tự động hóa", "Công nghệ kỹ thuật cơ điện tử"],
            "cơ khí": ["Công nghệ kỹ thuật cơ khí", "Công nghệ chế tạo máy"],
            "máy móc": ["Công nghệ kỹ thuật cơ khí", "Công nghệ chế tạo máy"],
            "công trình": ["Kỹ thuật xây dựng", "Kỹ thuật xây dựng công trình giao thông"],
            "xây dựng": ["Kỹ thuật xây dựng", "Kỹ thuật xây dựng công trình giao thông"],
            "cầu đường": ["Kỹ thuật xây dựng công trình giao thông"],
            "giao thông": ["Kỹ thuật xây dựng công trình giao thông", "Quy hoạch và quản lý giao thông"],
            "vận tải": ["Logistics và hạ tầng giao thông", "Quy hoạch và quản lý giao thông"],
            "logistics": ["Logistics và hạ tầng giao thông"],
            "kinh doanh": ["Quản trị kinh doanh", "Marketing", "Thương mại điện tử"],
            "quản lý": ["Quản trị kinh doanh", "Quản trị nhân lực"],
            "marketing": ["Marketing", "Thương mại điện tử"],
            "tiếng anh": ["Ngôn ngữ Anh"],
            "ngoại ngữ": ["Ngôn ngữ Anh"]
        }
        
        # Tìm các từ khóa liên quan đến sở thích trong tin nhắn
        matched_interests = []
        for keyword, nganh_list in so_thich_nganh_mapping.items():
            if keyword in message:
                matched_interests.extend(nganh_list)
        
        # Loại bỏ các ngành trùng lặp và lấy tối đa 5 ngành
        recommended_nganh = list(dict.fromkeys(matched_interests))[:5]
        
        if recommended_nganh:
            message = "Dựa trên sở thích của bạn, tôi gợi ý các ngành sau:\n\n"
            for i, nganh in enumerate(recommended_nganh, 1):
                message += f"{i}. {nganh}\n"
                
            message += "\nBạn có muốn biết thêm thông tin về ngành nào trong số này không?"
        else:
            message = "Tôi chưa xác định được sở thích rõ ràng của bạn. Bạn có thể cho tôi biết bạn thích gì hoặc quan tâm đến lĩnh vực nào không?"
        
        dispatcher.utter_message(text=message)
        return []



class ActionTuVanTheoMonVaDiem(Action):
    """
    Hành động tư vấn ngành học dựa trên điểm 3 môn cụ thể và tự động quy ra khối thi
    """
    def name(self) -> Text:
        return "action_tu_van_theo_mon_va_diem"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Lấy tin nhắn của người dùng
        message = tracker.latest_message.get('text', '').lower()
        
        # Định nghĩa các mã khối thi và môn tương ứng
        khoi_thi = {
            "A00": ["toán", "lý", "hóa"],
            "A01": ["toán", "lý", "anh"],
            "B00": ["toán", "hóa", "sinh"],
            "C00": ["văn", "sử", "địa"],
            "C01": ["văn", "toán", "lý"],
            "C02": ["văn", "toán", "hóa"],
            "D01": ["toán", "văn", "anh"],
            "D07": ["toán", "hóa", "anh"],
            "D08": ["toán", "sinh", "anh"],
            "D09": ["toán", "sử", "anh"],
            "D10": ["toán", "địa", "anh"]
        }
        
        # Định nghĩa các từ khóa cần nhận dạng cho các môn học
        mon_tu_dong = {
            "toán": ["toán", "toan", "đại số", "dai so", "hình học", "hinh hoc", "math"],
            "lý": ["lý", "ly", "vật lý", "vat ly", "physics"],
            "hóa": ["hóa", "hoa", "hóa học", "hoa hoc", "chemistry"],
            "sinh": ["sinh", "sinh học", "sinh hoc", "biology"],
            "văn": ["văn", "van", "ngữ văn", "ngu van", "literature"],
            "sử": ["sử", "su", "lịch sử", "lich su", "history"],
            "địa": ["địa", "dia", "địa lý", "dia ly", "geography"],
            "anh": ["anh", "tiếng anh", "tieng anh", "english"]
        }
        
        # Tìm kiếm các môn học trong tin nhắn
        found_subjects = {}
        
        for mon, keywords in mon_tu_dong.items():
            for keyword in keywords:
                if keyword in message:
                    # Tìm điểm số gần với tên môn
                    diem_pattern = r'{}.*?(\d+(\.\d+)?)'.format(keyword)
                    diem_match = re.search(diem_pattern, message)
                    
                    if not diem_match:
                        # Tìm ngược lại: điểm trước rồi đến tên môn
                        diem_pattern = r'(\d+(\.\d+)?).*?{}'.format(keyword)
                        diem_match = re.search(diem_pattern, message)
                    
                    if diem_match:
                        found_subjects[mon] = float(diem_match.group(1))
                        break
        
        # Nếu không tìm thấy đủ 3 môn, thông báo cho người dùng
        if len(found_subjects) < 3:
            dispatcher.utter_message(text="Xin lỗi, tôi cần thông tin về 3 môn thi của bạn cùng với điểm số. Ví dụ: 'Tôi được Toán 8, Lý 7.5, Hóa 8.5'.")
            return []
        
        # Tính tổng điểm
        total_score = sum(found_subjects.values())
        
        # Xác định khối thi phù hợp
        matching_blocks = []
        for ma_khoi, mon_list in khoi_thi.items():
            if all(mon in found_subjects for mon in mon_list):
                khoi_score = sum(found_subjects[mon] for mon in mon_list)
                matching_blocks.append((ma_khoi, khoi_score))
        
        # Sắp xếp theo điểm từ cao xuống thấp
        matching_blocks.sort(key=lambda x: x[1], reverse=True)
        
        if not matching_blocks:
            dispatcher.utter_message(text="Xin lỗi, tôi không thể xác định được khối thi phù hợp từ các môn bạn đã nhập. Vui lòng thử lại với các môn thuộc một khối thi cụ thể.")
            return []
        
        # Đọc danh sách ngành
        nganh_list = load_nganh_data()
        if not nganh_list:
            dispatcher.utter_message(text="Hiện tại tôi không thể cung cấp thông tin về các ngành tuyển sinh. Xin vui lòng thử lại sau.")
            return []
        
        # Tạo response
        message = f"Từ các môn bạn đã nhập, tôi xác định được các khối phù hợp là:\n\n"
        
        for ma_khoi, khoi_score in matching_blocks[:3]:  # Chỉ hiển thị 3 khối phù hợp nhất
            message += f"- Khối {ma_khoi} ({', '.join(khoi_thi[ma_khoi])}) với tổng điểm: {khoi_score:.1f}\n"
        
        message += "\nDựa vào điểm các khối này, tôi tư vấn cho bạn các ngành sau ( tính theo năm 2024):\n\n"
        
        # Năm gần nhất trong dữ liệu
        latest_year = "2024"
        
        # Tìm các ngành phù hợp với khối và điểm
        recommended_nganh = []
        
        for ma_khoi, khoi_score in matching_blocks[:3]:  # Chỉ xét 3 khối đầu tiên
            for nganh in nganh_list:
                if ma_khoi in nganh["khoi_xet_tuyen"] and latest_year in nganh["diem_chuan"] and nganh["diem_chuan"][latest_year] is not None:
                    diem_chuan = nganh["diem_chuan"][latest_year]
                    
                    if khoi_score >= diem_chuan:
                        # Tránh ngành trùng lặp
                        if nganh["ten_nganh"] not in [n["ten_nganh"] for n in recommended_nganh]:
                            recommended_nganh.append({
                                "ten_nganh": nganh["ten_nganh"],
                                "ma_khoi": ma_khoi,
                                "diem_dat": khoi_score,
                                "diem_chuan": diem_chuan,
                                "chenh_lech": khoi_score - diem_chuan
                            })
        
        # Sắp xếp theo mức độ phù hợp (chênh lệch tăng dần)
        recommended_nganh.sort(key=lambda x: (-x["chenh_lech"], x["ten_nganh"]))
        
        if recommended_nganh:
            for i, nganh in enumerate(recommended_nganh[:26], 1):  # Giới hạn 10 ngành
                message += f"{i}. {nganh['ten_nganh']} - Khối {nganh['ma_khoi']}\n"
                message += f"   Điểm của bạn: {nganh['diem_dat']:.1f}, Điểm chuẩn: {nganh['diem_chuan']:.1f} (Chênh lệch: +{nganh['chenh_lech']:.1f})\n\n"
                
            message += "Bạn có muốn biết thêm thông tin về ngành nào trong số này không?"
        else:
            message += "Với điểm số hiện tại, bạn chưa đạt đủ điểm chuẩn các ngành của trường. Bạn có thể cân nhắc các phương thức xét tuyển khác như xét học bạ hoặc đánh giá năng lực."
        
        dispatcher.utter_message(text=message)
        return []