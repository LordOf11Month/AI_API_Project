# Stilometri Sayacı (Yazarlık Benzerlik Analizörü)

Bu proje, iki metin arasındaki yazım stilini karşılaştırarak aynı yazar tarafından yazılıp yazılmadığını analiz eden bir stilometri aracıdır.

## 🔍 Temel Özellikler (MVP)

Projenin ilk sürümü (Minimum Viable Product) aşağıdaki temel yeteneklere sahip olacaktır:

-   **Girdi:** Karşılaştırılacak iki farklı metin (örnek: iki ayrı blog yazısı, makale veya e-posta).
-   **Çıktı:**
    -   **Benzerlik Skoru:** Metinlerin stilistik olarak ne kadar benzediğini gösteren 0 ile 1 arasında bir skor.
    -   **Yazarlık Olasılığı:** Analiz sonucunda metinlerin aynı yazar tarafından yazılmış olma ihtimalini yüzde (%) olarak gösteren bir değer.
    -   **Analiz Edilen Özellikler:** Skorun hesaplanmasında kullanılan metriklerin dökümü (örneğin: kelime çeşitliliği, ortalama cümle uzunluğu, n-gram sıklığı vb.).

## ⚙️ Teknik Stack

Proje, modern ve etkili teknolojiler kullanılarak geliştirilecektir:

| Bileşen            | Teknoloji Seçenekleri                                                              |
| ------------------ | ---------------------------------------------------------------------------------- |
| **Backend**        | Node.js + Express. Gerekirse Python tabanlı analiz modeli bir Flask API ile sarmalanabilir. |
| **Analiz Algoritması** | - **İstatistiksel:** TF-IDF, N-gram, Zipf Yasası.<br>- **AI Tabanlı:** `bert-base-turkish` embedding + Cosine Similarity. |
| **API Entegrasyonu** | Swagger UI kullanılarak interaktif ve anlaşılır API dokümantasyonu sağlanacaktır. |

## 📂 Dosya Yapısı

Projenin GitHub reposu aşağıdaki gibi organize edilecektir:

```plaintext
/stilometri-sayaci
├── /backend          # Node.js API katmanı
│   ├── app.js        # API rotaları ve Express sunucusu
│   └── /utils        # Analiz fonksiyonları ve yardımcı modüller
├── /model            # Python tabanlı analiz motoru
│   ├── feature_extraction.py   # Metinlerden özellik çıkaran script
│   └── similarity_calculator.py # Benzerlik skorunu hesaplayan script
└── README.md         # Proje özellikleri ve kurulum talimatları
```

## 🚀 Adım Adım Geliştirme Planı

1.  **Veri Toplama:**
    -   Modeli test etmek ve doğruluğunu ölçmek için Kaggle gibi platformlardan İngilizce veya Türkçe yazar verisetleri bulunacaktır (örnek: [CCAT50 Turkish News Text Classification](https://www.kaggle.com/datasets/savasy/ccat50-turkish-news-text-classification)).

2.  **Model Prototipi Geliştirme:**
    -   Yazarlık stilini temsil eden anlamsal vektörler (embeddings) oluşturmak için `sentence-transformers` ve Türkçe BERT modeli kullanılacaktır.
    -   İki metnin embedding'leri arasındaki benzerlik, Cosine Similarity ile ölçülecektir.

    ```python
    # Örnek: Cosine Similarity ile embedding karşılaştırma
    from sentence_transformers import SentenceTransformer
    import numpy as np

    # Modeli yükle
    model = SentenceTransformer('emrecan/bert-base-turkish-cased')

    # Metinleri vektörlere dönüştür
    embedding1 = model.encode("Merhaba dünya!")
    embedding2 = model.encode("Selam gezegen!")

    # Cosine similarity hesapla
    similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

    print(f"Benzerlik Skoru: {similarity}")
    ```

3.  **API Entegrasyonu:**
    -   Node.js tabanlı ana backend, analiz işlemleri için Python ile geliştirilen modele (Flask API üzerinden) HTTP istekleri göndererek haberleşecektir. Bu sayede iki dilin de güçlü yanları bir arada kullanılacaktır. 