import requests
import os

# 测试API
def test_api():
    base_url = "http://localhost:8080"

    # 健康检查
    response = requests.get(f"{base_url}/health")
    print(f"Health check: {response.status_code}, {response.json()}")

    # 上传图像测试
    if os.path.exists("image.png"):
        with open("image.png", "rb") as f:
            files = {"image": f}
            data = {"watermark_type": "istock"}

            response = requests.post(
                f"{base_url}/api/v1/remove-watermark",
                files=files,
                data=data
            )

            print(f"Upload response: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Result: {result}")

                # 下载结果
                if result.get('success'):
                    task_id = result.get('task_id')
                    download_response = requests.get(
                        f"{base_url}/api/v1/download/{task_id}"
                    )

                    if download_response.status_code == 200:
                        with open(f"result_{task_id}.png", "wb") as f:
                            f.write(download_response.content)
                        print(f"Result saved as result_{task_id}.png")

if __name__ == "__main__":
    test_api()