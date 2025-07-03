# Easy-VS-Configuration

**Easy-VS-Configuration** là một ứng dụng giúp bạn dễ dàng cấu hình và quản lý các thư viện từ [vcpkg](https://github.com/microsoft/vcpkg) trong Visual Studio 2022. Ứng dụng hỗ trợ quá trình phát triển phần mềm C++ hiệu quả hơn bằng cách đơn giản hóa việc cài đặt và tích hợp thư viện.

---

## 🛠️ Hướng dẫn cài đặt và sử dụng

### 1. Clone vcpkg từ GitHub

Mở **Command Prompt (cmd)** hoặc **PowerShell**, sau đó chạy:

```sh
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
bootstrap-vcpkg.bat
```

> 🔔 **Lưu ý:** Nếu bạn dùng Linux/macOS, hãy chạy:
>
> ```sh
> ./bootstrap-vcpkg.sh
> ```

---

### 2. Tải và cài đặt Easy-VS-Configuration

```sh
git clone https://github.com/phsang198/Easy-VS-Configuration.git
cd Easy-VS-Configuration
pip install -r requirements.txt
python app.py
```

---

### 3. Sử dụng

* Nhấn **Setting** → thêm đường dẫn đến thư mục `vcpkg` → **OK**.
* Nhấn **Browse** để mở file dự án `.vcproj` hoặc `.sln`.
* Nhập các thư viện cần cài đặt (ví dụ: `fmt`, `cpr`, `curl`) → nhấn **Add library** để tự động cài đặt và tích hợp vào dự án.
* Bạn cũng có thể sử dụng các lệnh vcpkg trực tiếp từ giao diện (vcpkg command).

---

## 📷 Giao diện minh họa

![alt text](image.png)

---
