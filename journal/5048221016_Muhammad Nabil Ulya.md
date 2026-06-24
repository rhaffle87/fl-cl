## **PROPOSAL TUGAS AKHIR – EL234799** 

# **PERANCANGAN PRIVATE CLOUD DAN IMPLEMENTASI INFRASTRUCTURE AS A SERVICE UNTUK SKALA KAMPUS** 

## **MUHAMMAD NABIL ULYA** 

NRP 5048221016 

Dosen Pembimbing 

**Dr.Ir. Achmad Affandi, DEA.** NIP 196510141990021001 

Dosen Pembimbing II 

**Dr. Ir. Endroyono, DEA.** NIP 196504041991021001 

## **Program Studi Sarjana Teknik Telekomunikasi** 

Departemen Teknik Elektro 

Fakultas Teknologi Elektro dan Informatika Cerdas 

Institut Teknologi Sepuluh Nopember 

Surabaya 

1 

Tahun 2025 

## **LEMBAR PENGESAHAN** 

## **JUDUL PROPOSAL TUGAS AKHIR DITULIS SINGKAT JELAS DAN MENGGAMBARKAN TEMA POKOK** 

## **PROPOSAL TUGAS AKHIR** 

Diajukan untuk memenuhi salah satu syarat 

untuk **mengerjakan dan mengikuti evaluasi** Tugas Akhir pada 

Program Studi S-1 Teknik Telekomunikasi 

Departemen Teknik Elektro Fakultas Teknik Elektro dan Informatika Cerdas Institut Teknologi Sepuluh Nopember 

## Oleh : **MUHAMMAD NABIL ULYA** 

NRP. 5048221016 

Disetujui oleh Tim Penguji Proposal Tugas Akhir : 

1. Dr. Ir. Achmad Affandi, DEA. Pembimbing 2. Dr. Ir. Endroyono, DEA. Ko-pembimbing 3. Nama dan gelar penguji Penguji 4. Nama dan gelar penguji Penguji 5. Nama dan gelar penguji Penguji 

## **SURABAYA** 

**Bulan, Tahun** 

i 

## **ABSTRAK** 

## **ANALISA PENGARUH PANJANG LINKAGE TERHADAP RESPON SERIES ACTIVE VARIABLE GEOMETRY SUSPENSION (SAVGS)** 

**Nama Mahasiswa / NRP : Muhammad Nabil Ulya/5048221016 Departemen : Teknik Elektro FTEIC - ITS Dosen Pembimbing : Dr. Ir. Achmad Affandi, DEA.** 

## **Abstrak** 

Kebutuhan komputasi di lingkungan perguruan tinggi terus meningkat sehingga diperlukan infrastruktur yang fleksibel, terpusat, dan mudah dikelola. Penelitian ini merancang dan mengimplementasikan private cloud berbasis Proxmox Virtual Environment (Proxmox VE) dengan layanan Infrastructure as a Service (IaaS) menggunakan dua node server fisik. Untuk menjaga konsistensi cluster dua node, diterapkan mekanisme QDevice sebagai suara tambahan quorum. Selain itu, konfigurasi NIC bonding dengan protokol LACP (IEEE 802.3ad) digunakan untuk meningkatkan throughput dan redundansi jaringan. Sistem pencadangan diintegrasikan menggunakan Proxmox Backup Server (PBS) dengan skema full dan incremental backup. Pengujian performa dilakukan menggunakan _sysbench_ , _fio_ , dan _iperf3_ , sedangkan keandalan cluster diuji melalui simulasi kegagalan node serta proses backup–restore. Hasil menunjukkan bahwa rancangan private cloud mampu menyediakan layanan IaaS yang stabil, memiliki peningkatan kinerja jaringan melalui LACP, serta mendukung pemulihan data yang efisien. Implementasi ini dinilai layak untuk digunakan sebagai infrastruktur komputasi di lingkungan kampus. 

## **Kata kunci** _**: Proxmox VE, IaaS, QDevice, LACP, NIC Bonding, Proxmox Backup Server.**_ 

ii 

## **ABSTRACT** 

## **ANALYSIS OF THE EFFECT OF LINKAGE LENGTH ON SERIES ACTIVE VARIABLE GEOMETRY SUSPENSION (SAVGS) RESPONSE** 

**Student Name / NRP : Muhammad Nabil Ulya/5048221016 Department : Teknik Elektro FTEIC - ITS Advisor : Dr. Ir. Achmad Affandi, DEA.** 

## **Abstract** 

The increasing demand for computing resources in higher education institutions requires an infrastructure that is flexible, centralized, and easy to manage. This study designs and implements a private cloud based on the Proxmox Virtual Environment (Proxmox VE) to provide Infrastructure as a Service (IaaS) using two physical server nodes. To maintain consistency within the two-node cluster, a QDevice is implemented as an additional quorum vote. Furthermore, NIC bonding using the LACP (IEEE 802.3ad) protocol is employed to enhance network throughput and link redundancy. A centralized backup mechanism is integrated through the Proxmox Backup Server (PBS) using full and incremental backup schemes. Performance testing is conducted using _sysbench_ , _fio_ , and _iperf3_ , while cluster reliability is evaluated through node failure simulations and backup–restore processes. The results demonstrate that the proposed private cloud architecture can deliver stable IaaS services, achieve improved network performance through LACP, and support efficient data recovery. Therefore, this implementation is suitable for adoption as a computing infrastructure in a campus environment. 

## **Keywords:** _**Proxmox VE, IaaS, QDevice, LACP, NIC Bonding, Proxmox Backup Server.**_ 

iii 

## **DAFTAR ISI** 

|LEMBAR PENGESAHAN|||i|
|---|---|---|---|
|ABSTRAK|||ii|
|ABSTRACT|||iii|
|DAFTAR ISI|||iv|
|DAFTAR GAMBAR|||vi|
|DAFTAR TABEL|||vii|
|DAFTAR SIMBOL|||viii|
|BAB 1<br>PENDAHULUAN|||9|
|1.1<br>Latar Belakang|||9|
|1.2<br>Rumusan Masalah|||10|
|1.3<br>Batasan Masalah|||10|
|1.4<br>Tujuan|||10|
|1.5<br>Manfaat|||11|
|BAB 2<br>TINJAUAN PUSTAKA|||12|
|2.1<br>Hasil Penelitian Terdahulu|||12|
|2.2<br>Cloud Computing|||13|
|2.2.1<br>Cloud publik|||13|
|2.2.2<br>Cloud private|||13|
|2.2.3<br>Hybrid Cloud|||13|
|2.3<br>Layanan dalam Cloud Computing|||14|
|_2.3.1_<br>_Infrasructure as a Service_(IaaS)|||14|
|2.3.2<br>_Platform as a Service_(PaaS)|||15|
|2.3.3<br>Software as a Service (SaaS)|||16|
|2.4<br>Proxmox VE sebagai Platform Private Cloud|||18|
|2.4.1<br>Keunggulan Proxmox VE sebagai Private|Cloud**Error!**|**Bookmark**|**not**|
|**defined.**||||
|2.5<br>Virtualisasi dan Hypervisor|**Error! Bookmark not defined.**|||
|2.5.1<br>KVM (Kernel-based Virtual Machine)|**Error! Bookmark not defined.**|||
|2.6<br>Cluster Proxmox VE dalam Dua Node Environment**Error!**||**Bookmark**|**not**|
|**defined.**||||
|2.6.1<br>Inti Arsitektur Cluster Proxmox VE|**Error! Bookmark not defined.**|||
|2.7<br>NIC Aggregation|||20|



iv 

|2.7.1<br>Prinsip Kerja dan Manfaat NIC Aggregation|20|
|---|---|
|2.8<br>Storage pada Proxmox VE|21|
|2.8.1<br>Arsitektur Storage Virtual Machine|21|
|2.9<br>Proxmox Backup Server (PBS)|21|
|BAB 3<br>METODOLOGI|22|
|3.1<br>Metode Penelitian|22|
|3.2<br>Bahan dan Alat yang Digunakan|23|
|3.2.1<br>Perangkat Keras|23|
|3.2.2<br>Perangkat Lunak|23|
|3.3<br>Perancangan Sistem|24|
|3.3.1<br>Arsitektur Sistem|24|
|3.3.2<br>Perancangan Topologi Jaringan|25|
|3.3.3<br>Perancangan Konfigurasi Jaringan dan Cluster|26|
|3.3.4<br>Perancangan Penyimpangan dan Pencadangan|27|
|3.3.5<br>Rancangan Pengujian Kinerja dan Keandalan|27|
|3.3.6<br>Urutan pelaksanaan penelitian|28|
|DAFTAR PUSTAKA|29|
|LAMPIRAN|31|



v 

## **DAFTAR GAMBAR** 

vi 

## **DAFTAR TABEL** 

vii 

## **DAFTAR SIMBOL** 

viii 

## **BAB 1 PENDAHULUAN** 

## **1.1 Latar Belakang** 

Perkembangan teknologi informasi (IT) di perguruan tinggi semakin berkembang seiring jaman, kebutuhan komputasi untuk pembelajaran daring, laboratorium virtual, penelitian, serta administrasi meningkat baik dari segi jumlah pengguna maupun variasi beban kerja. Banyak institusi masih mengandalkan server fisik terpisah atau solusi _hosted public cloud_ yang menyebabkan isu privasi data, biaya operasional, dan ketergantungan pihak ketiga. Cloud computing mucul sebagai solusi modern yang menyediakan sumber daya komputasi secara terpusat on-demand, sehingga perguruan tinggi dapat meningkatkan efisiensi dan ketersediaan layanan mereka tanpa bergantung pada sistem fisik tradisional. 

Banyak perguruan tinggi yang masih menggunakan infrastuktur _on-premise_ yang menimbulkan isu masalah seperti pemeliharaan yang tinggi, keterbatasan skalabilitas, dan utilitas sumber daya yang rendah. Eyvazov dkk. mengungkapkan bahwa kebutuhan pembelajaran digital terutama ketika permintaan layanan yang meningkat dan ketika metode jarak jauh dibutuhkan, sistem tradisional tidak mampu menyelesaikan kebutuhan tersebut [1]. Konsep seperti _private cloud_ dan penyajian layanan _Infrastuctur as a Service (IaaS)_ menjadi relevan karena institusi bisa punya control penuh atas konfigurasi jaringan, infrastuktur, dan kebijakan keamanan serta menyediakan sumber daya _on-demand_ bagi mahasiswa, dosen, dan peneliti [2]. 

Sejumlah penelitian terdahulu menunjukkan bahwa implementasi _private cloud_ di lingkungan kampus dapat meningkatkan efisiensi pengelolaan layanan digital dan fleksibilitas, tetapi keberhasilannya sangat ditentukan oleh pemilihan platform, model arsitektur jaringan dan strategi backup yang diterapkan. Oleksiuk dkk. menyebutkan implementasi Proxmox VE di lingkungan kampus menawarkan kemudahan deployment, cluster management, dan mekanisme backup yang efisien sehingga sangat cocok untuk kebutuhan pendidikan [3]. Studi dari Maliszewski dkk. juga menyebutkan bahwa _NIC aggregation_ pada _private cloud_ membuktikan bahwa desain jaringan yang tepat mampu meningkatkan _throughput_ secara signifikan dan mengurangi resiko _bottleneck_ pada beban komputasi yang tinggi [4]. 

Kampus yang tidak memiliki rancangan private cloud yang tepat, bisa menyebabkan berbagai masalah seperti sulitnya menyediakan _virtual machine_ (VM) secara cepat untuk keperluan perkuliahan, terhambatnya kegiatan praktikum karena keterbatasan sumber daya fisik, tingginya resiko kehilangan data akibat ketiadaan sistem backup terpusat, dan berkurang nya stabilitas layanan _e-learning_ yang bergantung pada performa server. Tanpa ketersediaan arsitektur dan platform yang terukur, layanan digital kampus menjadi tidak andal dan menyulitkan operasional akademik. Hal ini sejalan dengan studi yang menekankan bahwa desain private cloud yang kurang optimal dapat menyebabkan ketidakstabilan layanan, inefiensi penggunaan sumber daya, dan meningkatnya biaya pemeliharaan [5]. 

Berdasarkan kebutuhan dan permasalahan tersebut, penelitian ini dilakukan untuk merancang private cloud berbasis Proxmox VE yang mampu menyediakan layanan IaaS secara efisien, stabil, dan mudah dikelola pada lingkungan kampus. Termasuk di dalamnya perancangan arsitektur server, konfigurasi jaringan dengan dukungan _NIC aggregation,_ penyusunan _backup_ menggunakan _Proxmox Backup Server,_ dan evaluasi performa dasar untuk memastikan layanan IaaS dapat mendukung kebutuhan akademik secara optimal. Penelitian ini 

9 

diharapkan dapat memberikan solusi komprehensif dalam pengembangan infrastruktur private cloud kampus yang praktis dan siap diimplementasikan. 

## **1.2 Rumusan Masalah** 

Berdasarkan latar belakang dan tujuan pengembangan private cloud berbasis Proxmox VE untuk skala kampus, rumusan masalah penelitian ini dirumuskan sebagai berikut: 

1. Bagaimana merancang arsitektur private cloud berbasis Proxmox VE dengan cluster dua node yang mampu menyediakan layanan _Infrastructure as a Service_ (IaaS) untuk kebutuhan kampus? 

2. Bagaimana mekanisme quorum dapat dipertahankan pada cluster dua node (menggunakan QDevice) sehingga mengurangi risiko kehilangan layanan saat salah satu mati? 

3. Bagaimana mengonfigurasi jaringan (NIC aggregation/LACP) dan storage agar throuhput, isolasi layanan _virtual machine_ (VM), dan ketersediaan memadai untuk scenario praktikum dan perkuliahan? 

4. Bagaimana penerapan Proxmox Backup Server (PBS) untuk backup/restore VM yang efisien dalam lingkungan dengan storage lokal? 

5. Bagaimana performa dan keandalan layanan IaaS pada private cloud berbasis Proxmox VE dengan arsitektur tiga node dalam skenario _High Availbility_ (HA) ideal di lingkungan kampus? 

## **1.3 Batasan Masalah** 

Agar penulisan tugas akhir ini tetap terukur, penulis mengonsep batasan masalah untuk memberikan arah yang lebih terfokus. Berikut merupakan batasan-batasan masalah yang diberikan: 

1. Penelitian fokus pada perancangan private cloud dan implementasi IaaS, bukan SaaS (Software as a Service) dan PaaS (Platform as a Service). 

2. Menggunakan Proxmox VE sebagai platform private cloud dan KVM sebagai hypervisor utama. 

3. Implementasi dua fisik node fisik untuk cluster Proxmox, penggunaan QDevice (VM/host kecil) untuk quorum tambahan. 

4. Penggunaan local-lvm atau ZFS lokal pada node untuk storage, storage terdistribusi lain tidak diimplementasikan. 

5. Backup menggunakan PBS sebagai remote backup dengan skema backup yang diuji full (awal) dan incremental/dedup. 

6. Pengujian jaringan fokus pada LACP (IEEE 802.3ad) untuk NIC aggregation; integrasi dengan backbone kampus (hybrid cloud/routing cloud) tidak dilakukan. 

7. _High Availability_ dievaluasi pada skenario node failure tunggal (single node failure) dengan asumsi quorum ganjil aktif, tanpa pengujian skala besar atau multi-failure. 

## **1.4 Tujuan** 

Tujuan dari penelitian ini adalah untuk: 

1. Merancang arsitektur private cloud berbasis Proxmox VE yang mampu memberikan layanan IaaS bagi kebutuhan akademik kampus, termasuk praktikum, penelitian, dan pengembangan proyek mahasiswa maupun dosen 

10 

2. Merancang dan mengonfigurasi cluster Proxmox dua node yang andal dan stabil, termasuk penerapan mekanisme quorum menggunakan QDevice untuk mencegah split-brain. 

3. Mengimplementasikan konfigurasi jaringan berbasis NIC aggregation (LACP) untuk meningkatkan throuhput, redudansi, dan ketersediaan koneksi jaringan pada lingkungan virtualisasi. 

4. Menerapkan sistem penyimpanan dan pencadangan berbasis Proxmox Backup Server (PBS) untuk memastikan efisiensi data, keamanan data, dan restore VM yang cepat dan terukur. 

5. Melakukan pengujian performa dan keandalan untuk memastikan rancangan IaaS dapat digunakan secara optimal pada kampus. 

## **1.5 Manfaat** 

Penelitian ini diharapkan memberi manfaat sebagai berikut: 

## Manfaat Praktis: 

1. Memberikan solusi infrastruktur private cloud yang efisien untuk kampus, sehingga penyedia VM untuk mata kuliah, keperluan praktikum, dan penelitian dapat dilakukan secara cepat, terkontrol, dan terstandarisasi. 

2. Meningkatkan pemanfaatan sumber daya server kampus melalui virtualisasi KVM, manajemen cluster dan NIC bonding sehingga perangkat kelas yang tersedia dapat dimanfaatkan secara optimal. 

3. Menyediakan mekanisme backup terpusat menggunakan PBS, sehingga resiko kehilangan data VM dapat diredam dan proses restore layanan dapat dilakukan lebih cepat. 

## Manfaat Akademik 

4. Menjadi referensi implementasi IaaS berbasis Proxmox VE bagi penelitian selanjutnya, terutama untuk desain private cloud skala kampus. 

5. Memberikan contoh nyata penerapan teknologi cloud computing dalam lingkungan kampus, guna dapat digunakan sebagai bahan ajar atau studi kasus pada mata kuliah terkait jaringan, cloud, dan virtualisasi. 

## Manfaat Institusional 

6. Mendukung transformasi digital kampus dengan menyediakan infrastruktur cloud internal cloud internal yang dapat digunakan guna riset dan pengembangan laboratorium virtual, layanan e-learning, maupun riset berbasis komputasi. 

7. Meningkatkan kemandirian pengelolaan IT kampus, karena model _deployment_ private cloud memungkinkan kontrol penuh tanpa ketergantungan pada layanan publik atau vendor eksternal. 

11 

## **BAB 2 TINJAUAN PUSTAKA** 

## **2.1 Hasil Penelitian Terdahulu** 

Untuk mendukung judul penelitian, penulis melakukan studi literatur yang berhubungan dengan judul pada proposal tugas akhir ini. Terdapat beberapa jurnal penelitian yang berhubungan dengan perancangan _Private Cloud_ dan implementasi _Infrasructure as a Service (IaaS)_ untuk skala kampus yang telah dilakukan sebelumnya, beberapa referensi yang akan dilakukan dalam tugas akhir yaitu: 

1. Achieving Seamless Migration To Private-Cloud Infrastucture For Multi-Campus Univesities, oleh Niki Kyriakou, Zoi Lachana, Dimitrios N. Skoutas, Charlampos Skianis dan Yannis Charalabidis. 

Penelitian ini memposisikan migrasi ke infrastuktur _private cloud_ sebagai solusi yang menawarkan skalabilitas, fleksibilitas, dan control aspek keamanan serta pemenuhan _Service Level Agreement (SLA)_ , sehingga kampus dapat merespons perubahan kebutuhan layanan TI dengan lebih cepat dan hemat biaya. Dalam tahap implementasi, universitas membangun pusat data terpusat yang dirancang khusus untuk kebutuhan pendinginan, daya, dan redundansi, menggantikan model server terpisah di tiap kampus. Infrastuktur baru mengkonsolidasikan server, _storage,_ dan jaringan menggunakan teknologi virtualisasi (VMware vSphere ESXi), sehingga memungkinkan pembentukan cluster yang menampung ratusan mesin virtual dengan kapasitas yang dapat diperluas. Selain itu, dilakukan upgrade backbone jaringan hingga 10-25 Gbps, penggantian border router, serta penyediaan akses nirkabel yang lebih luas. Hasil implementasi menunjukkan peningkatan efisiensi alokasi kapasitas, kemampuan pemulihan bencana yang lebih baik, redundansi sumber daya, dan kesiapan untuk evolusi menuju arsitektur _hybrid cloud._ Penelitian juga menyoroti sejumlah tantangan teknis dan organisasi seperti keterbatasan _bandwidth,_ keterbatasan SDM ahli _cloud,_ integrasi system _legacy,_ kebutuhan standarisasi, dan interoperabilitas data. Penulis menutup studi dengan rekomendasi agar institusi lain yang hendak bermigrasi melakukan perencanaan matang, migrasi bertahap, dan mempertimbangkan integrasi layanan _public cloud_ untuk membentuk model hybrid yang lebih fleksibel [2]. 

2.   Comparative Study of the Support of Academic Clouds Based on Apache CloudStack and Proxmox VE Platforms oleh Vasyl P. Oleksiuk, Olesia R. Oleksiuk dan M.Spirin. 

Penelitian ini menyajikan studi komparatif penerapan _private cloud_ berbasis _Apache CloudStack_ dan _Proxmox VE_ pada lingkungan pendidikan, kedua platform tersebut pada dasarnya mampu menyediakan jumlah virtual machine yang setara untuk kebutuhan pembelajaran namun menunjukkan _trade-off_ antara perforna mentah dan kemudahan operasional.  Dari hasil pengujian _benchmark, Cloudstack_ unggul pada beberapa metrik (missal rata-rata permintaan web ~2115,7 req/s dibandingkan ~1787,6 req/s pada _Proxmox_ , sekitar 18% lebih tinggi), sedangkan _Proxmox_ unggul pada aspek kemudahan deployment, dukungan mobile, antarmuka administrasi, dan alat backup terintegrasi seperti _Proxmox Backup Server_ menyebabkan operasional harian menjadi lebih sederhana. Sederhana nya, penulis merinci tugas-tugas pemiliharaan akademik cloud mulai dari LDAP/Active Directory, pembuatan template dan control akses VM, hingga desain model performa guna menghitung kapasitas VM berdasarkan frekuensi CPU dan memori host serta tantangan backup yang menuntut kombinasi skema (full, differential, incremential) dan terkadang pemanfaatan storage cloud (missal 

12 

Google Drive) guna mengatasi keterbatasan infrastruktur lokal, implikasi langsung dari temuan ini bagi penelitian perancangan IaaS skala kampus adalah penting nya mengevaluasi bukan hanya metrik performa, tetapi juga faktor-faktor operasional seperti automasi pemeliharaan, strategi backup ketika memilih atau mengadaptasi platform untuk lingkungan akademik, dan metrik performa [6]. 

## **2.2 Cloud Computing** 

_Cloud computing_ adalah penyediaan layanan untuk berbagai hal yang melibatkan layanan komputasi seperti server, penyimpanan, database, dan perangkat lunak melalui internet “sesuai permintaan”. _Cloud computing_ menggunakan jaringan untuk menghubungkan _user_ ke platform _cloud_ untuk mengakses layanan dan meminta komputasi yang disewa. Ada tiga model _deployment cloud computing_ yang disesuaikan sesuai kebutuhan _user_ , perusahaan atau organisasi, diantara lain; 

## **2.2.1 Cloud publik** 

adalah layanan yang tersedia dengan cara bayar sesuai pemakaian untuk umum [7]. Penyedia cloud menawarkan _resource_ komputasi, penyimpanan, dan jaringan melalui internet yang memungkinkan perusahaan mengakses resource bersama sesuai kebutuhan dan sasaran bisnis mereka. 

## **2.2.2 Cloud private** 

dirancang untuk menjaga infromasi sensitif maupun kepatuhan regulasi organisasi atau perusahaan, hal yang tidak disediakan oleh _cloud_ lainnya yang bisa saja tidak menjaga nya secara efektif [5]. 

## **2.2.3 Hybrid Cloud** 

adalah kombinasi setidaknya satu _cloud private_ dan satu _cloud_ publik. Dalam _hybrid cloud_ , suatu organisasi menyediakan dan mengelola beberapa sumber daya secara eksternal dan beberapa secara internal. Misalnya, organisasi yang menyimpan data sumber daya manusia dan manajemen hubungan pelanggan di _cloud_ publik tetapi memiliki data pribadi di _private cloud_ nya [7]. 

13 

**Gambar 2.1** Ilustrasi arsitektur dan _model deployment_ pada _cloud computing_ Sumber: https://ventiontech.com/cdn/shop/articles/cloud-computing-1_36ad37ab03f6-4e82-896a-c5a40c98c776.png?v=1740362016&width=400 

Dari segi model _deployment,_ penulis memilih private cloud karena relevansi nya terhadap keperluan kampus yang membutuhkan kontrol penuh terhadap infrastruktur, keamanan, dan manajemen sumber daya yang sangat penting untuk lingkungan kampus. 

## **2.3 Layanan dalam Cloud Computing** 

Penyedia layanan cloud computing menawarkan beberapa model, _termasuk Infrasructure as a Service (IaaS), Platform as a Service (PaaS), Software as a Service (SaaS)_ , setiap model di dirancang untuk keperluan tertentu [8]. Layanan tersebut memberikan kebebasan _user_ untuk menyesuaikan _resource_ sesuai permintaan, mengurangi pembiayaan awal, dan kompleksitas operasional. 

## _**2.3.1 Infrasructure as a Service**_ **(IaaS)** 

IaaS adalah model _cloud computing_ yang menyediakan layanan sewaan sumber daya infrastuktur IT dasar seperti server, penyimpanan, dan jaringan melalui internet, dengan model pembayaran sesuai penggunaan. IaaS telah mengalami kemajuan yang signifikan terutama dengan integrasi otomisasi, _artificial intelligence (AI)_ dan _virtual machine (VM)_ untuk manajemen infrastruktur. IaaS menyediakan kontrol server sepenuhnya saat penggunaan _resource_ komputasi yang tervirtualisasi (perangkat keras), mulai dari _server_ , jaringan, hingga penyimpanan. IaaS menawarkan kontrol paling besar karena sumber daya dikelola oleh _user,_ tetapi bisa mengalami masalah akibat manufaktur dibagikan. Biasanya digunakan untuk kebutuhan seperti _hosting websites_ dan pengolahan data besar [8]. 

## **2.3.1.1 Komponen Utama IaaS** 

Ada empat komponen utama dalam _IaaS_ , diantara nya: 

14 

- Komputasi: Ini adalah komponen paling dasar dari IaaS, dan menyediakan _virtual machine (VM)_ bagi bisnis untuk menjankan aplikasi. 

- Penyimpanan: Penyedia IaaS menawarkan beragam opsi penyimpanan, termasuk penyimpanan blok yang ideal untuk menyimpan data dalam jumlah besar yang perlu diakses dengan cepat, penyimpanan berkas ideal untuk keperluan membagikan antar _user_ , dan penyimpanan objek idal untuk menyimpan data tidak terstruktur dalam jumlah besar seperti gambar dan video. 

- Jaringan: Penyedia IaaS menawarkan beragam opsi jaringan, termasuk jaringan privat virtual (VPN) yang memungkinkan bisnis menghubungkan jaringan lokal mereka ke _cloud,_ penyeimbang beban yang mendistribusikan lalu lintas ke beberapa VM, dan _firewall_ yang melindungi jaringan dari akses tidak sah. 

- Administrasi: Penyedia IaaS menawarkan beragam layanan administrasi, seperti pemantauan yang memungkinkan bisnis melacak kinerja infrastruktur IaaS mereka, layanan pencadangan memungkinkan bisnis membuat salinan data mereka keperluan pemulihan bencana, dan pemulihan bencana yang memungkinkan bisnis memulihkan data dan aplikasi mereka jika terjadi bencana. 

## **2.3.1.2 Kelebihan dan Kekurangan dari IaaS** 

Infrastructure as a Service (IaaS) memiliki sejumlah kelebihan yang menjadikannya model layanan yang banyak digunakan dalam pengelolaan infrastruktur komputasi modern. Salah satu keunggulan utamanya adalah skalabilitas yang tinggi, sehingga pengguna dapat menambah atau mengurangi kapasitas komputasi sesuai kebutuhan tanpa harus melakukan investasi perangkat keras secara langsung. IaaS juga menawarkan tingkat keandalan yang baik karena penyedia layanan telah membangun infrastruktur yang stabil, berlapis, dan dilengkapi mekanisme redundansi untuk meminimalkan gangguan layanan. Selain itu, aspek keamanan menjadi salah satu fitur yang diutamakan, di mana penyedia IaaS menyediakan fasilitas seperti firewall, enkripsi data, serta sistem deteksi intrusi untuk melindungi sumber daya pengguna dari ancaman keamanan. 

Meskipun memiliki banyak keunggulan, IaaS juga memiliki beberapa keterbatasan. Pengguna tetap bertanggung jawab untuk mengelola sistem operasi, konfigurasi keamanan internal, dan layanan pendukung seperti basis data atau middleware. Sebagian besar penyedia layanan hanya menyediakan infrastruktur dasar berupa server virtual, jaringan, dan penyimpanan, sehingga manajemen atas aplikasi dan keamanan internal tetap menjadi tanggung jawab pengguna. Kondisi ini menuntut pengguna memiliki kompetensi teknis yang memadai untuk memastikan sistem berjalan dengan aman dan optimal. 

## **2.3.2** _**Platform as a Service**_ **(PaaS)** 

(PaaS) adalah metode _cloud computing_ yang menyediakan platform komputasi yang lengkap untuk membangun, mengelola, dan mengoperasikan aplikasi melalui internet. PaaS memungkinkan _user_ untuk mengelola solusi terintegrasi atau _solution track_ yang mencakup _operation system (OS), middleware, database,_ hingga _tools_ pengembangan aplikasi tanpa perlu membeli dan mengelola infrastruktur fisik. _PaaS_ telah berkembang pesat seiring dengan munculnya _microservices_ dan _containerization,_ yang mempermudah pengembangan dan penerapan apliksi secara cepat [8]. 

## **2.3.2.1 Komponen utama PaaS** 

Berikut merupakan komponen urama yang biasanya disediakan oleh PaaS: 

15 

- _Opereation System:_ Paas menawarkan sistem operasi yang telah diatur untuk mendukung jalannya aplikasi. 

- Alat pengembangan: Platform ini dilengkapi dengan _tools_ pengembangan seperti editor kode, alat pengujian, dan manajemen versi untuk mempermudah proses _coding_ dan _debugging._ 

- _Middleware:_ Adalah perangkat lunak perantara yang menghubungkan aplikasi dengan sistem operasi atau layanan lainnya 

- _Database Management System (DBMS): PaaS_ menawarkan manajemen basis data yang memungkinkan pengguna menyimpan dan mengelola data aplikasi tanpa perlu mengatur _server_ basis data secara manual. 

- _Framework_ Pengembangan: Pemngembangan memanfaatkan _framework_ yang sudah tersedia, seperti Django, Ruby on Rails, atau Node,js, untuk mempercepat pengembangan aplikasi. 

- Orkestrasi Kontainer: Banyak platform mendukung kontainer seperti Kubernetes untuk mengelola aplikasi berbasis container secara otomatis dan efisien. 

## **2.3.2.2 Kelebihan dan Kekurangan dari PaaS** 

PaaS menawarkan kelebihan berupa percepatan proses pengembangan aplikasi karena pengembang dapat langsung memanfaatkan alat, framework, dan lingkungan kerja yang telah tersedia. Model ini juga memberikan akses mudah ke layanan tambahan seperti analitik atau kecerdasan buatan tanpa perlu investasi besar. PaaS mendukung kolaborasi tim dari berbagai lokasi, menyediakan alat untuk seluruh siklus hidup aplikasi, dan menyederhanakan integrasi komponen sehingga proses pengembangan menjadi lebih efisien. 

Di sisi lain, PaaS memiliki kekurangan seperti tingginya ketergantungan pada penyedia layanan yang dapat membatasi fleksibilitas teknologi dan meningkatkan risiko vendor lock-in. Pengguna juga memiliki kontrol terbatas terhadap infrastruktur, sehingga beberapa kebutuhan keamanan atau konfigurasi khusus sulit dilakukan. Selain itu, biaya dapat meningkat seiring penggunaan layanan tambahan, dan risiko keamanan tetap ada karena data dan proses pengembangan berada pada infrastruktur pihak ketiga. 

## **2.3.3 Software as a Service (SaaS)** 

SaaS adalah model pengiriman perangkat lunak dimana aplikasi diakses melalui internet dari penyedia layanan cloud, alih-alih diinstal dan dikelola secara lokal. _User_ mengakses aplikasi melalui langganan tanpa perlu khawatir tentang infrastruktur, pembaruan, atau perawatan karena penyedia menangani semuanya. SaaS menjadi model layanan cloud paling banyak digunakan, dengan perkiraan ukuran pasar akan mencapai $307,3 miliar pada tahun 2026 [8]. 

## **2.3.3.1 Komponen Utama PaaS** 

Berikut adalah komponen utama dari PaaS 

- Infrastuktur: SaaS mudah disesuaikan dengan kebutuhan bisnis dan dapat ditingkatkan atau diturunkan skalanya tergantung persyaratan bisnis. 

- _Customer Relationship Management (CRM):_ SaaS menyediakan platform umum untuk beberapa penyewa, maka diperlukan satu repositori untuk beberapa akun pengguna dan detail akun untuk manajemen. 

16 

- Penyediaan Otomatis: SaaS secara otomatis memungkinkan proses _on-boarding user_ yang mudah untuk membangun layanan pengiriman berbasis cloud 

- Dukungan dan Analisis: SaaS menyediakan perangkat untuk manajemen platform dan pemeriksaan metrik. 

## **2.3.3.2 Kelebihan dan Kekurangan SaaS** 

SaaS memiliki kelebihan utama berupa proses implementasi yang cepat karena seluruh sistem sudah disediakan dan dikelola oleh penyedia layanan. Pengguna tidak perlu melakukan instalasi, konfigurasi, atau pengembangan awal, sehingga cukup berlangganan paket yang sesuai dan langsung dapat mengakses aplikasi melalui peramban web. Selain itu, biaya penggunaan SaaS cenderung lebih mudah diprediksi karena menggunakan model berlangganan yang disesuaikan dengan kebutuhan pengguna. Beban biaya awal seperti pembelian perangkat keras, instalasi, dan pemeliharaan juga dapat dihindari karena seluruh infrastruktur ditangani oleh penyedia layanan. SaaS juga unggul dalam hal skalabilitas, memungkinkan pengguna menambah fitur atau jumlah pengguna sesuai perkembangan organisasi tanpa harus melakukan investasi tambahan pada perangkat keras. 

Meskipun menawarkan banyak kemudahan, SaaS memiliki beberapa kekurangan yang perlu dipertimbangkan. Pengguna memiliki kontrol yang terbatas terhadap konfigurasi sistem dan lingkungan aplikasi, sehingga fitur tertentu mungkin tidak dapat disesuaikan secara mendalam. Ketergantungan pada penyedia layanan juga menjadi risiko, terutama jika terjadi gangguan layanan atau perubahan kebijakan yang memengaruhi akses dan biaya. Selain itu, penyimpanan data pada infrastruktur pihak ketiga dapat menimbulkan kekhawatiran terkait privasi dan keamanan, terutama bagi organisasi yang memerlukan perlindungan data yang lebih ketat. Ketergantungan pada koneksi internet juga dapat menjadi kendala karena SaaS memerlukan akses jaringan yang stabil untuk beroperasi secara optimal. 

**Gambar 2.2** Ilustrasi perbedaan layanan cloud computing beserta pembagian tanggung jawab antara penyediaan dan _user_ 

Sumber: https://b3549173.smushcdn.com/3549173/wpcontent/uploads/2024/12/pengertian-cloud-computing.webp?lossy=2&strip=1&webp=1 

17 

Untuk layanan _cloud computing,_ penulis menggunakan layanan Infrastructure as a Service (IaaS) karena relevansi penyediaan _resource_ komputasi seperti _VM, storage,_ dan jaringan yang fleksibel sehingga lebih efisien untuk berbagai penelitian, praktikum, dan proyek internal. Cloud computing dalam pendidikan adalah cara yang efektif dalam teknologi dan biaya untuk mengatur operasi sistem digital tanpa perlu mengeluarkan biaya besar untuk pengembangan infrastruktur IT [3]. 

## **2.4 Platform Private Cloud yang digunakan** 

Platform private cloud dalam penelitian ini dipilih berdasarkan kebutuhan penyediaan layanan _Infrastructure as a Service_ (IaaS) yang stabil, terkelola, dan _mendukung High Availability_ (HA) ideal pada lingkungan kampus. Pada praktiknya, terdapat beberapa platform yang umum digunakan untuk membangun infrastruktur cloud dan virtualisasi, antara lain Proxmox VE, Kubernetes, dan Docker. Masing-masing memiliki karakteristik, tujuan, dan tingkat abstraksi yang berbeda. 

## **2.4.1 Platform Virtualisasi & Cloud Management** 

Berikut beberapa platform virtualisasi dan cloud management yang bisa menjadi perbandingan untuk penelitian ini: 

## **2.4.1.1 Proxmox Virtual Environment** 

Proxmox _Virtual Environment_ (Proxmox VE) sering digunakan sebagai solusi private cloud yang efisien dan hemat biaya, platform _open-source_ ini dirancang untuk manajemen virtualisasi _server_ dan _container_ secara terpusat. Dibangun di atas Debian Linux dan mengintegrasikan dua teknologi utama: KVM (Kernel-based Virtual Machine) untuk virtualisasi penuh dan _Linux Containers_ (LXC) untuk _conteinerisasi_ ringan. Proxmox VE menyediakan _interface_ manajemen terpusat berbasis web, yang memudahkan pengelolaan VM, _container, backup, live migration_ serta konfigurasi _high-availbility_ (HA) dalam satu sistem yang terintegrasi [9]. 

Selain itu, Proxmox VE mendukung pembentukan cluster multi-node dengan mekanisme quorum berbasis Corosync, yang memungkinkan penerapan High Availability secara native tanpa memerlukan perangkat lunak tambahan dari pihak ketiga. .Efisiensi biaya menawarkan biaya investasi awal yang rendah dari total _cost of ownership_ (TCO) yang lebih kecil dibandingkan soluso komersial seperti VMware ESXi atau Microsoft Hyper-V, namun tetap memberikan return on investment (ROI) yang tinggi [10]. 

## **2.4.1.2 Kubernetes** 

Kubernetes merupakan platform orkestrasi container yang berfokus pada manajemen aplikasi berbasis container. Kubernetes bekerja pada lapisan _Platform as a Service (PaaS)_ dan membutuhkan infrastruktur virtualisasi atau fisik di bawahnya. Meskipun Kubernetes memiliki mekanisme high availability dan scalability yang kuat, platform ini tidak dirancang untuk menyediakan IaaS, melainkan untuk mengelola lifecycle aplikasi container. Dalam konteks penelitian ini, Kubernetes tidak dipilih karena: 

1. Kubernetes tidak menyediakan manajemen VM sebagai layanan utama. 

2. Kompleksitas operasionalnya relatif tinggi untuk skala kampus. 

18 

## **2.4.1.3 Docker** 

Docker merupakan teknologi containerization yang berfungsi untuk menjalankan aplikasi dalam lingkungan terisolasi yang ringan. Docker bukan platform cloud management, melainkan runtime container, dan tidak menyediakan mekanisme cluster, quorum, atau _High Availability_ tingkat infrastruktur secara native tanpa orchestrator tambahan seperti Kubernetes atau Docker Swarm. Oleh karena itu, Docker tidak digunakan dalam penelitian ini karena: 

1. Tidak mendukung layanan IaaS secara langsung. 

2. Tidak menyediakan mekanisme HA berbasis quorum. 

3. Tidak sesuai untuk evaluasi infrastruktur virtualisasi skala kampus. 

## **2.4.2 Alasan Pemilihan Proxmox VE sebagai Platform Penelitian** 

Pemilihan Proxmox VE dalam penelitian ini bukan didasarkan pada kelengkapan fitur semata, melainkan pada kesesuaian arsitektural dengan tujuan penelitian dan karakteristik lingkungan kampus. Berikut beberapa keunggulan nya pada penelitian ini: 

- Pertama, Proxmox VE merupakan platform open-source, sehingga memungkinkan audit konfigurasi, transparansi sistem, serta pengembangan dan pembelajaran yang selaras dengan prinsip akademik. Hal ini menjadi keunggulan dibandingkan solusi proprietary seperti VMware vSphere. 

- Kedua, Proxmox VE menyediakan _High Availability orchestration_ secara native, tanpa ketergantungan pada solusi tambahan. Mekanisme HA dikelola langsung oleh Proxmox HA Manager yang terintegrasi dengan Corosync dan quorum cluster. 

- Ketiga, Proxmox VE mendukung arsitektur quorum ganjil (tiga node), yang merupakan prasyarat utama _High Availability_ ideal. Dengan quorum ganjil, sistem mampu mempertahankan konsistensi cluster dan melakukan _failover_ VM secara deterministik ketika salah satu node mengalami kegagalan. 

- Keempat, Proxmox VE mengintegrasikan manajemen cluster, virtualisasi, jaringan, dan backup dalam satu stack. Integrasi ini menyederhanakan desain sistem, memudahkan evaluasi performa, serta mengurangi kompleksitas operasional. 

- Kelima, dari sisi biaya, Proxmox VE menawarkan _Total Cost of Ownership (TCO)_ yang lebih rendah dibandingkan platform proprietary maupun solusi cloud orchestration kompleks seperti OpenStack, sehingga lebih realistis untuk diterapkan pada lingkungan kampus. 

## **2.4.3 Standarisasi Platform sebagai Acuan Evaluasi** 

Evaluasi platform Proxmox VE dalam penelitian ini mengacu pada standar dan kerangka kerja yang relevan. bukan untuk menyatakan sertifikasi, melainkan sebagai dasar evaluasi akademik. ISO/IEC 17788 dan ISO/IEC 17789 (Cloud Computing Overview & Architecture), standar ini digunakan sebagai acuan konseptual dalam menilai kesesuaian Proxmox VE sebagai platform cloud. Evaluasi difokuskan pada: 

- Resource pooling, yaitu kemampuan Proxmox VE dalam mengelola sumber daya komputasi secara terpusat dan dibagi ke banyak VM. 

- Measured service, yaitu kemampuan pemantauan dan pengukuran penggunaan CPU, memori, storage, dan jaringan pada VM. 

19 

- Elasticity, yaitu kemampuan sistem dalam menyediakan dan menyesuaikan resource VM sesuai kebutuhan beban kerja. 

## **2.5 Cluster Proxmox VE dengan Quorum Ganjil** 

Cluster Proxmox VE menggunakan Corosync sebagai protokol komunikasi antar node dan pmxcfs (Proxmox Cluster File System) sebagai sistem file terdistribusi untuk menyinkronkan konfigurasi cluster, termasuk definisi VM, jaringan, dan storage. Quorum ganjil merupakan arsitektur yang dirancang untuk menyediakan High Availability (HA) ideal pada lingkungan virtualisasi. Dalam konfigurasi ini, tiga node Proxmox VE digabungkan ke dalam satu cluster terpusat yang memungkinkan layanan virtual machine (VM) tetap tersedia meskipun terjadi kegagalan pada salah satu node. 

Arsitektur tiga node memenuhi prinsip mayoritas suara (majority voting) pada mekanisme quorum, sehingga cluster dapat mempertahankan konsistensi konfigurasi dan mengambil keputusan secara deterministik tanpa risiko split-brain. Dengan quorum ganjil, sistem tetap berada dalam kondisi _quorate_ selama minimal dua node aktif, yang menjadi prasyarat utama High Availability pada sistem terdistribusi. 

## **2.5.1 High Availbility pada Cluster Tiga Node** 

_High Availbility_ pada Proxmox VE dikelola oleh Proxmox HA Manager, yang bertugas memantau status node dan resource virtual machine secara kontinu. Dalam cluster tiga node, HA Manager mampu melakukan: 

- Deteksi kegagalan node secara otomatis, 

- Restart atau migrasi VM ke node yang sehat, 

- Menjaga kontinuitas layanan tanpa kehilangan konsistensi data konfigurasi. 

Failover pada cluster tiga node bersifat deterministik, karena keputusan diambil berdasarkan mayoritas quorum yang valid. Hal ini membedakan arsitektur ini dari konfigurasi dengan quorum genap atau solusi berbasis workaround. Dengan demikian, cluster Proxmox VE tiga node memenuhi karakteristik High Availability ideal, yaitu toleransi terhadap kegagalan satu node tanpa menghentikan layanan utama. 

## **2.6 NIC Aggregation** 

NIC ( _Network Interface Card_ ) aggregation atau lebih dikenal sebagai _Link Aggregation_ adalah teknik menggabungkan beberapa NIC atau port fisik menjadi satu link untuk meningkatkan bandwidth, redudansi dan kendala jaringan. Protokol yang umum digunakan adalah _Link Aggregation Control Protocol_ (LACP), yaitu protokol standar (IEEE 802.3ad) yang mengatur pemeliharaan dan pembentukan grup agregasi secara otomatis [14]. 

## **2.6.1 Prinsip Kerja dan Manfaat NIC Aggregation** 

Prinsip kerja dan manfaat sebagai berikut: 

- Bandwith yang lebih besar dengan menggabungkan beberapa NIC, kapasitas transmisi meningkat yang membuat throughput jaringan menjadi lebih tinggi [14]. 

- Redudansi dan failover bisa diatasi jika salah satu link fisik gagal dengan lalu lintas yang otomatis dialihkan ke link lain dalam grup agregasi. 

20 

- Load Balancing: beban lalu lintas jaringan dapat didistribusikan secara merata ke seluruh link yang tergabung, mengurangi resiko bottleneck pada satu jalur. 

## **2.7 Storage pada Proxmox VE** 

Proxmox VE (Virtual Environment) menyediakan arstitektur storage yang fleksibel dan terintegrasi untuk mendukung kebutuhan VM. Storage virtual memiliki peran krusial dalam performa, reliabilitas, serta kemampuan backup pada sebuah private cloud. Pada Proxmox VE, storage untuk virtual machine dapat menggunakan local storage, LVM-Thin, maupun ZFS. 

## **2.7.1 Arsitektur Storage Virtual Machine** 

Proxmox VE mendukung berbagai jenis storage untuk VM, baik lokal maupun jaringan yang terhubung dalam satu cluster. Storage yang umum meliputi: 

- Local storage yang menggunakan disk fisik lokal pada node Proxmox untuk menyimpan disk image VM, template container, dan ISO. 

- Network storage meliputi protokol seperti CIFS, iSCSI, dan NFS untuk membagi storage antar node, memungkinkan live migration dan HA [15]. 

- Distribute storage seperti GlusterFS dan Ceph dapat digunakan untuk meningkatkan  skalabilitas dan ketersediaan data. 

Arsitektur storage pada Proxmox VE memungkinkan VM dan container menyimpan data pada berbagai backend storage, baik block storage (misal LVM, iSCSI, DRBD) maupun filebased storage (NFS, GlusterFS). Storage clustering meningkatkan efisiensi, ketersediaan, dan skalabilitas, serta memudahkan manajemen data dan migrasi VM antar node [15]. 

## **2.8 Proxmox Backup Server (PBS)** 

Proxmox Backup Server adalah solusi _backup_ terpusat yang dirancang khusus untuk lingkungan Proxmox VE. Fungsinya sebagai berikut: 

- _Backup_ dan _Restore VM/Container_ : Mendukung backup terjadwal (scheduled backup) dan snapshot VM secara efisien, baik secara penuh (full) maupun incremental, sehingga menghemat ruang penyimpanan dan bandwidth [3]. 

- Integrasi dengan Proxmox VE: Backup dapat dilakukan secara otomatis dari Proxmox VE ke Proxmox Backup Server melalui jaringan, mendukung pemulihan cepat (disaster recovery) jika terjadi kegagalan sistem [3]. 

- Keamanan dan Efisiensi: Data backup dapat dienkripsi dan dikompresi, serta mendukung deduplikasi untuk mengoptimalkan penggunaan storage [3]. 

- Manajemen Terpusat: Memudahkan pengelolaan backup seluruh VM dan container dalam satu platform, serta mendukung _backup off-site_ untuk perlindungan data ekstra [3]. 

PBS sangat penting untuk menjaga integritas dan ketersediaan data pada infrastruktur virtualisasi, serta mempercepat proses pemulihan pasca bencana. 

21 

## **BAB 3 METODOLOGI** 

## **3.1 Metode Penelitian** 

Penelitian ini menggunakan metode eksperimen dengan pendekatan implemetasi langsung. Metode ini dipilih bertujuan untuk merancang, membangun, dan menguji performa private cloud berbasis Proxmox VE secara nyata, sehingga setiap variabel sistem (jaringan, cluster, backup, dan storage) dapat diamati serta diukur langsung. Metode eksperimen dilakukan melalui tahapan berikut: 

**Diagram 1** Tahapan penelitian 

Tahapan penelitian pada tugas akhir ini disusun secara sistematis agar proses perancangan hingga evaluasi infrastruktur private cloud berbasis Proxmox VE dapat dilaksanakan secara terukur dan konsisten. Secara umum, penelitian ini terdiri dari enam tahapan utama sebagai berikut; 

Tahap pertama adalah studi literatur, yaitu mengkaji jurnal ilmiah, dokumentasi resmi, dan penelitian terdahulu terkait Proxmox VE, arsitektur cluster dua node, mekanisme quorum menggunakan QDevice, konfigurasi NIC bonding/LACP, manajemen storage virtual, serta Proxmox Backup Server (PBS). Tahap ini bertujuan untuk memperoleh dasar teori yang kuat sebagai fondasi perancangan sistem. Tahap kedua adalah analisis kebutuhan, yang mencakup identifikasi perangkat keras dan perangkat lunak yang diperlukan berdasarkan batasan masalah penelitian. Analisis ini meliputi kebutuhan server fisik, NIC bonding, storage lokal (LVM/ZFS), jaringan terkelola, serta spesifikasi PBS sebagai target pencadangan. Tahap ketiga adalah perancangan sistem, yang meliputi penyusunan arsitektur cluster dua node, perancangan topologi jaringan berbasis LACP, konfigurasi mekanisme quorum menggunakan QDevice, serta desain strategi backup. Pada tahap ini ditetapkan rancangan teknis yang akan diterapkan pada tahap implementasi. Tahap keempat adalah implementasi sistem, yaitu proses instalasi Proxmox VE pada kedua node fisik, konfigurasi jaringan dan bonding, pembentukan cluster, aktivasi QDevice, serta integrasi Proxmox Backup Server. Tahap ini menghasilkan lingkungan 

22 

private cloud yang siap diuji. Tahap kelima adalah pengujian, yang meliputi pengukuran performa komputasi mesin virtual, throughput jaringan pada NIC bonding, stabilitas cluster terhadap skenario failover, serta evaluasi proses backup dan restore menggunakan PBS. Pengujian dilakukan untuk menilai kemampuan sistem dalam memberikan layanan IaaS secara nyata. Tahap terakhir adalah analisis dan kesimpulan, yaitu mengevaluasi seluruh hasil pengujian untuk menentukan apakah rancangan private cloud yang dibangun telah memenuhi kebutuhan layanan IaaS pada lingkungan kampus. Analisis ini menjadi dasar penarikan kesimpulan penelitian dan rekomendasi untuk pengembangan lebih lanjut. 

## **3.2 Bahan dan Alat yang Digunakan** 

Untuk mendukung proses perancangan dan implementasi sistem private cloud berbasis Proxmox VE, penelitian ini membutuhkan seperangkat alat dan bahan yang terdiri dari perangkat keras dan perangkat lunak. Bagian berikut menjelaskan komponen yang digunakan dengan fungsinya dalam keseluruhan sistem. 

## **3.2.1 Perangkat Keras** 

Dibawah merupakan tabel untuk perangkat keras pada penelitian ini: 

**Tabel 1** Perangkat keras yang digunakan 

|**No.**|**Perangkat**|**Jenis**|**Spesifikasi**|**Fungsi**|
|---|---|---|---|---|
|1|Server<br>(dua<br>node)|Server<br>Dell<br>PowerEdge<br>R630|CPU<br>multicore,<br>RAM>16 GB, 2x<br>NIC|Menjalankan cluster Proxmox<br>VE dan VM.|
|2|Server (satu<br>node)|Server<br>Dell<br>PowerEdge||Menjalankan cluster Proxmox<br>VE dan PBS|
|3|Router|||Menghubungkan private cloud<br>ke<br>jaringan<br>kampus<br>dan<br>berfungsi<br>sebagai<br>default<br>gateway.|
|4|Managed<br>Switch|Switch||Melakukan agregasi NIC (NIC<br>bonding LACP) dari kedua node<br>Proxmox.|
|5|Kabel<br>&<br>Konektivitas<br>Fisik|||Menghubungkan NIC server ke<br>switch<br>Menghubungkan<br>switch<br>ke<br>router<br>Menghubungkan laptop QDevice<br>ke switch<br>Memberikan konektivitas fisik<br>untuk LACP, corosync, dan VM<br>traffic|



## **3.2.2 Perangkat Lunak** 

Dibawah merupakan untuk tabel perangkat lunak pada penilitian ini: 

**Tabel 2** Software yang akan digunakan 

|**No.**|**Software**|**Fungsi**|
|---|---|---|
|1|Proxmox<br>Virtual<br>Environment<br>(Proxmox VE)|Hypervisor KVM.|



23 

|||Manajemen node, cluster, VM, storage,<br>network.|
|---|---|---|
|2|Proxmox Backup Server (PBS)|Backup full<br>Backup incremental<br>Deduplication<br>Restore VM<br>Verification & integrity check|
|3|Cluster Services: Corosync & pmxcfs|Komunikasi cluster dua node.<br>Penyimpanan konfigurasi cluster.<br>Mekanisme quorum.|
|4|Proxmox HA Manager|Monitoring node & VM<br>Restart/failoverVMotomatis saatnode gagal|



## **3.3 Perancangan Sistem** 

Perancangan sistem pada penelitian ini dilakukan untuk membangun layanan private cloud berbasis Infrastructure as a Service (IaaS) yang memiliki tingkat ketersediaan tinggi (High Availability) dan sesuai dengan kebutuhan operasional di lingkungan kampus. Sistem dirancang menggunakan cluster Proxmox Virtual Environment (VE) tiga node, sehingga mampu mempertahankan layanan meskipun terjadi kegagalan pada salah satu node. 

## **3.3.1 Arsitektur Sistem** 

Arsitektur sistem terdiri dari tiga node fisik Proxmox VE yang tergabung dalam satu cluster dan saling berkomunikasi menggunakan protokol Corosync. Setiap node memiliki peran yang setara sebagai host virtual machine, anggota quorum, dan kandidat failover. 

Dengan jumlah node ganjil (tiga node), cluster mampu mencapai quorum secara alami, sehingga sistem tetap beroperasi meskipun satu node mengalami kegagalan. Kondisi ini memungkinkan Proxmox HA Manager untuk melakukan restart atau migrasi virtual machine secara otomatis ke node yang masih aktif. 

Komponen utama arsitektur sistem meliputi: 

- Node Proxmox VE (3 node): Berfungsi sebagai infrastruktur komputasi yang menjalankan virtual machine berbasis KVM/QEMU. 

- Cluster Management (Corosync & HA Manager): Mengelola komunikasi antar node, pemantauan status node, dan mekanisme failover. 

- Jaringan tersegmentasi (VLAN): Digunakan untuk memisahkan trafik manajemen, layanan VM, dan storage. 

- Proxmox Backup Server (PBS): Menyediakan layanan backup dan restore VM secara terpusat untuk menjaga keamanan data. 

Arsitektur ini dirancang untuk mencerminkan kondisi nyata infrastruktur kampus, di mana keterbatasan sumber daya tetap harus mampu memberikan layanan yang andal dan berkelanjutan 

24 

## **3.3.2 Perancangan Topologi Jaringan** 

Perancangan topologi jaringan pada penelitian ini bertujuan untuk mendukung implementasi cluster Proxmox VE tiga node yang menyediakan layanan Infrastructure as a Service (IaaS) dengan kemampuan High Availability (HA). Topologi dirancang agar komunikasi antar node berjalan stabil, terisolasi, dan mampu mendukung proses manajemen cluster, layanan virtual machine, serta mekanisme failover. 

Topologi jaringan menggunakan satu managed switch sebagai pusat konektivitas, yang mendukung fitur VLAN (Virtual Local Area Network) dan Link Aggregation Control Protocol (LACP). Seluruh node Proxmox VE terhubung ke switch melalui dua antarmuka jaringan fisik, yaitu eno1 dan eno2, yang dikonfigurasi sebagai NIC bonding dengan mode 802.3ad (LACP). Konfigurasi ini menghasilkan satu antarmuka logis bond0 yang berfungsi sebagai VLAN trunk, sehingga mampu membawa beberapa VLAN secara bersamaan. 

## **3.3.3 Segmentasi Jaringan Berbasis VLAN** 

Untuk memisahkan jenis trafik dan meningkatkan keandalan sistem, jaringan dibagi menjadi beberapa VLAN sebagai berikut: 

1. VLAN 10 – Management dan Cluster Network: VLAN ini digunakan untuk akses administrasi Proxmox VE serta komunikasi cluster menggunakan Corosync. Seluruh node Proxmox VE memiliki antarmuka vmbr0 yang terhubung ke VLAN ini. Karena berperan dalam penentuan quorum dan stabilitas cluster, VLAN ini bersifat kritis dan dipisahkan dari trafik layanan lainnya. 

2. VLAN 20 – Virtual Machine Network: VLAN ini digunakan sebagai jaringan layanan untuk virtual machine yang berjalan di atas cluster Proxmox VE. Antarmuka vmbr1 pada setiap node terhubung ke VLAN 20 dan digunakan oleh VM untuk melayani kebutuhan pengguna, seperti praktikum dan layanan internal kampus. 

3. VLAN 30 – Backup Network: VLAN ini digunakan untuk trafik backup yang berasal dari virtual machine menuju Proxmox Backup Server (PBS). Antarmuka vmbr2 pada setiap node terhubung ke VLAN 30, sehingga trafik backup tidak mengganggu jaringan manajemen maupun jaringan layanan VM. 

4. VLAN 40 – Migration Network (opsional)VLAN ini disediakan sebagai opsi untuk mendukung proses live migration virtual machine antar node, sehingga proses migrasi tidak membebani jaringan layanan utama. 

Topologi jaringan digambarkan sebagai berikut: 

25 

**Gambar 3.1** Topologi Jaringan Perancangan 

## **3.3.4 Perancangan Konfigurasi Jaringan dan Cluster** 

## **3.3.4.1 NIC Bonding (802.3ad LACP)** 

Setiap node menggabungkan dua NIC fisik menjadi satu interface logis (bond0) menggunakan protokol LACP. Dengan konfigurasi ini, sistem mendapatkan throuhput lebih besar dibanding single link atau redudansi keika salah satu kabel/port mengalami kegagalan. 

## **3.3.4.2 VLAN dan Bridge** 

Setiap VLAN diimplementasikan sebagai sub-interface pada bond0. Setiap VLAN kemudian di bridge ke vmbr yang digunakan oleh VM: 

- vmbr0 → Management 

- vmbr1 → VM Network 

26 

## • vmbr2 → Storage/Backup 

## **3.3.5 Perancangan Penyimpangan dan Pencadangan** 

## **3.3.5.1 Storage Lokal Node** 

Masing masing node menggunakan _local storage_ (LVM atau ZFS) untuk menjalankan VM. Ini dipilih lokal sesuai batasan yang tidak mencakup implementasi shared storage seperti Ceph, GlusterFS, dan NFS. 

## **3.3.5.2 Proxmox Backup Server (PBS)** 

Untuk mekanisme pencadangan, digunakan PBS yang ditempatkan pada jaringan VLAN 30. Skema pencadangan mengikuti: 

- Full Backup pada pencadangan awal atau periode tertentu, 

- Incremental Backup harian, 

- deduplikasi berbasis blok untuk mengurangi penggunaan kapasitas storage. 

PBS menyediakan fitur verifikasi ( _integrity check_ ), retensi backup, serta mekanisme restore yang akan dievaluasi pada tahapan pengujian. Skema retensi yang digunakan dapat berupa: 

- harian: 14 hari, 

- mingguan: 4–8 siklus, 

- bulanan: 1–2 set. 

Mekanisme ini mendukung tujuan penelitian yaitu menilai keandalan backup serta kemudahan proses pemulihan VM. 

## **3.3.6 Rancangan Pengujian Kinerja dan Keandalan** 

Pengujian dilakukan untuk mengevaluasi kinerja dan keandalan layanan IaaS pada cluster Proxmox VE tiga node dengan High Availability. Rangkaian pengujian meliputi: 

- Pengujian kinerja komputasi, untuk mengukur performa CPU dan memori virtual machine yang berjalan di atas cluster. 

- Pengujian kinerja penyimpanan, untuk mengevaluasi performa baca dan tulis data pada media penyimpanan virtual machine. 

- Pengujian kinerja jaringan, untuk mengukur throughput jaringan antar virtual machine serta menilai efektivitas konfigurasi VLAN dan NIC bonding. 

- Pengujian keandalan sistem (High Availability), dengan mensimulasikan kegagalan salah satu node guna mengamati mekanisme failover dan kontinuitas layanan. 

- Pengujian pemulihan sistem, untuk mengevaluasi stabilitas cluster setelah node yang mengalami kegagalan diaktifkan kembali. 

- Pengujian backup dan restore, sebagai pengujian pendukung untuk memastikan mekanisme pencadangan dan pemulihan data virtual machine berjalan dengan baik. 

Hasil dari rangkaian pengujian tersebut digunakan untuk menganalisis kemampuan sistem dalam menyediakan layanan IaaS yang andal dan sesuai dengan kebutuhan lingkungan kampus. 

27 

## **3.3.7 Urutan pelaksanaan penelitian** 

**Tabel 3** Durasi Penelitian 

|Tahapan Kegiatan||||||||||Minggu ke-|Minggu ke-||||||
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
||1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16|
|Studi Literatur|||||||||||||||||
|Analisis Kebutuhan<br>Sistem|||||||||||||||||
|Perancangan Sistem|||||||||||||||||
|Implementasi Sistem|||||||||||||||||
|Pengujian Kinerja dan<br>Keandalan|||||||||||||||||
|Analisis Hasil<br>Penelitian|||||||||||||||||
|Penyusunan Laporan<br>Akhir|||||||||||||||||



28 

## **DAFTAR PUSTAKA** 

- [1] F. Eyvazov, T. E. Ali, F. I. Ali, and A. D. Zolta’n, “Cloud-Enabled Educational Transformation: Designing and Implementing a Comprehensive Framework for Learning Institutions,” in _International Conference on Engineering, Technology and Management, ICETM 2025_ , Institute of Electrical and Electronics Engineers Inc., 2025. doi: 10.1109/ICETM63734.2025.11051904. 

- [2] N. Kyriakou, Z. Lachana, D. N. Skoutas, C. Skianis, and Y. Charalabidis, “Achieving Seamless Migration to Private-Cloud Infrastructure for Multi-Campus Universities,” _International Journal on Cloud Computing: Services and Architecture_ , vol. 13, no. 2, pp. 25–38, Apr. 2023, doi: 10.5121/ijccsa.2023.13202. 

- [3] V. P. Oleksiuk and O. R. Oleksiuk, “The practice of developing the academic cloud using the Proxmox VE platform,” _Educational Technology Quarterly_ , vol. 2021, no. 4, pp. 605–616, Dec. 2021, doi: 10.55056/etq.36. 

- [4] A. M. Maliszewski, D. Griebler, E. Roloff, R. Da Rosa Righi, and P. O. A. Navaux, “Evaluation Model and Performance Analysis of NIC Aggregations in Containerized Private Clouds,” in _Proceedings - Symposium on Computer Architecture and High Performance Computing_ , IEEE Computer Society, 2023, pp. 101–107. doi: 10.1109/SBAC-PADW60351.2023.00025. 

- [5] T. E. Ali, A. H. Morad, and M. A. Abdala, “Efficient Private Cloud Resources Platform,” in _3rd International Conference on Electrical, Communication and Computer Engineering, ICECCE 2021_ , Institute of Electrical and Electronics Engineers Inc., Jun. 2021. doi: 10.1109/ICECCE52056.2021.9514093. 

- [6] V. Oleksiuk, O. Oleksiuk, and O. Spirin, “Comparative Study of the Support of Academic Clouds Based on Apache CloudStack and Proxmox VE Platforms,” INSTICC, Jul. 2023, pp. 349–361. doi: 10.5220/0012064300003431. 

- [7] S. Goyal, “Public vs Private vs Hybrid vs Community - Cloud Computing: A Critical Review,” _International Journal of Computer Network and Information Security_ , vol. 6, no. 3, pp. 20–29, Feb. 2014, doi: 10.5815/ijcnis.2014.03.03. 

- [8] R. Younis, M. Iqbal, K. Munir, M. A. Javed, M. Haris, and S. Alahmari, “A Comprehensive Analysis of Cloud Service Models: IaaS, PaaS, and SaaS in the Context of Emerging Technologies and Trend,” in _5th International Conference on Electrical, Communication and Computer Engineering, ICECCE 2024_ , Institute of Electrical and Electronics Engineers Inc., 2024. doi: 10.1109/ICECCE63537.2024.10823401. 

- [9] A. Bompotas, N. R. Kalogeropoulos, and C. Makris, “CommC: A Multi-Purpose COMModity Hardware Cluster,” _Future Internet_ , vol. 17, no. 3, Mar. 2025, doi: 10.3390/fi17030121. 

- [10] B. R. Chang, H. F. Tsai, and C. M. Chen, “Empirical analysis of server consolidation and desktop virtualization in cloud computing,” _Math Probl Eng_ , vol. 2013, 2013, doi: 10.1155/2013/947234. 

- [11] L. Abeni, “Virtualized real-time workloads in containers and virtual machines,” _Journal of Systems Architecture_ , vol. 154, Sep. 2024, doi: 10.1016/j.sysarc.2024.103238. 

- [12] G. Li _et al._ , “The Convergence of Container and Traditional Virtualization: Strengths and Limitations,” _SN Comput Sci_ , vol. 4, no. 4, Jul. 2023, doi: 10.1007/s42979-02301827-9. 

- [13] L. Lapriliana, D. Kucuk, and N. N. Diana, “Server Clustering in Cloud Computing Using Proxmox Based High Availability Method,” _JOINTECS) Journal of Information Technology and Computer Science_ , vol. 3, no. 1, 2018. 

- [14] N. Islam, M. Fazla Rabbi, S. Shamim, M. Saikat Islam Khan, and M. Abu Yousuf, “A Machine Learning Approach to Implementation of Link Aggregation Control Protocol over Software Defined Networking,” 2021. 

- [15] L. Z. A. Mardedi, “Analisa Kinerja System Gluster FS pada Proxmox VE untuk Menyediakan High Availability,” _MATRIK : Jurnal Manajemen, Teknik Informatika dan Rekayasa Komputer_ , vol. 19, no. 1, pp. 173–185, Nov. 2019, doi: 10.30812/matrik.v19i1.473. 

30 

## **LAMPIRAN** 

31 

