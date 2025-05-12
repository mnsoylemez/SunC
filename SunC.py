import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import numpy as np
import pvlib
from pvlib import location
import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D

def calculate_solar_vectors(loc_data, start_year):
    """Verilen konum ve yıl için güneş konumu vektörlerini hesaplar."""
    try:
        start_date = pd.Timestamp(f'{start_year}-01-01 00:00:00', tz='UTC')
        end_date = pd.Timestamp(f'{start_year + 1}-01-01 00:00:00', tz='UTC')
        times_utc = pd.date_range(start=start_date, end=end_date, freq='10min', inclusive='left')
        
        loc = location.Location(
            latitude=loc_data['latitude'],
            longitude=loc_data['longitude'],
            tz=loc_data['timezone'],
            altitude=0,
            name=loc_data['name']
        )
        
        times_local = times_utc.tz_convert(loc_data['timezone'])
        solpos = loc.get_solarposition(times_local)
        clearsky = loc.get_clearsky(times_local, model='ineichen', solar_position=solpos)
        
        solpos['daylight'] = clearsky['dni'] > 0
        daylight_solpos = solpos[solpos['daylight']].copy()
        
        zenith_rad = np.radians(daylight_solpos['apparent_zenith'])
        azimuth_rad = np.radians(daylight_solpos['azimuth'])
        
        x = np.sin(zenith_rad) * np.sin(azimuth_rad)  # Doğu-Batı (pozitif Doğu)
        y = np.sin(zenith_rad) * np.cos(azimuth_rad)  # Kuzey-Güney (pozitif Kuzey)
        z = np.cos(zenith_rad)  # Dikey (pozitif yukarı)
        
        vectors_df = pd.DataFrame({
            'x': x,
            'y': y,
            'z': z,
            'dni': clearsky.loc[daylight_solpos.index, 'dni']
        }, index=daylight_solpos.index)
        
        return vectors_df
        
    except Exception as e:
        print(f"Güneş vektörleri hesaplanırken hata oluştu: {e}")
        raise e

def get_panel_normal(ew_tilt_deg, ns_tilt_deg):
    """Doğu-Batı ve Kuzey-Güney eğim açılarına göre panel normal vektörünü hesaplar."""
    ew_rad = np.radians(ew_tilt_deg)  # Pozitif = Doğuya eğim
    ns_rad = np.radians(ns_tilt_deg)  # Pozitif = Kuzeye eğim
    
    normal = np.array([0, 0, 1])
    
    Ry = np.array([
        [np.cos(ew_rad), 0, np.sin(ew_rad)],
        [0, 1, 0],
        [-np.sin(ew_rad), 0, np.cos(ew_rad)]
    ])
    
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(ns_rad), -np.sin(ns_rad)],
        [0, np.sin(ns_rad), np.cos(ns_rad)]
    ])
    
    normal = Ry @ normal
    normal = Rx @ normal
    
    return normal

def calculate_energy(vectors_df, panel_efficiency_decimal, ew_tilt_deg=None, ns_tilt_deg=None):
    """Enerji üretimini hesaplar: izleme veya sabit konum için."""
    panel_area = 1.0
    time_interval = 1/6
    
    if ew_tilt_deg is None or ns_tilt_deg is None:
        cos_theta = 1.0
    else:
        panel_normal = get_panel_normal(ew_tilt_deg, ns_tilt_deg)
        sun_vectors = vectors_df[['x', 'y', 'z']].values
        cos_theta = np.clip(np.dot(sun_vectors, panel_normal), 0, 1)
    
    energy_wh = vectors_df['dni'] * cos_theta * panel_efficiency_decimal * panel_area * time_interval
    energy_df = pd.DataFrame({'enerji_wh': energy_wh}, index=vectors_df.index)
    
    return energy_df

def find_best_fixed_position(vectors_df, panel_efficiency_decimal):
    """En iyi sabit konumu (Doğu-Batı ve Kuzey-Güney eğimleri) bulur."""
    coarse_angles = np.arange(-90, 91, 5)
    best_energy = 0
    best_ew_tilt = 0
    best_ns_tilt = 0
    
    for ew_tilt in coarse_angles:
        for ns_tilt in coarse_angles:
            energy_df = calculate_energy(vectors_df, panel_efficiency_decimal, ew_tilt, ns_tilt)
            total_energy = energy_df['enerji_wh'].sum()
            if total_energy > best_energy:
                best_energy = total_energy
                best_ew_tilt = ew_tilt
                best_ns_tilt = ns_tilt
    
    fine_ew_angles = np.arange(max(-90, best_ew_tilt - 5), min(91, best_ew_tilt + 6), 1)
    fine_ns_angles = np.arange(max(-90, best_ns_tilt - 5), min(91, best_ns_tilt + 6), 1)
    
    for ew_tilt in fine_ew_angles:
        for ns_tilt in fine_ns_angles:
            energy_df = calculate_energy(vectors_df, panel_efficiency_decimal, ew_tilt, ns_tilt)
            total_energy = energy_df['enerji_wh'].sum()
            if total_energy > best_energy:
                best_energy = total_energy
                best_ew_tilt = ew_tilt
                best_ns_tilt = ns_tilt
    
    return best_ew_tilt, best_ns_tilt

def create_visualizations(location_name, monthly_data, best_ew_tilt, best_ns_tilt, custom_ew_tilt=None, custom_ns_tilt=None):
    """Veriler için çeşitli görselleştirmeler oluşturur."""
    visualizations = {}
    
    # 1. Aylık enerji üretim grafiği
    fig_monthly = plt.figure(figsize=(10, 6))
    ax = fig_monthly.add_subplot(1, 1, 1)
    ax.plot(monthly_data.index, monthly_data['enerji_wh_izleme'], 'b-', label='İzleme (Güneşe Dik)')
    ax.plot(monthly_data.index, monthly_data['enerji_wh_sabit_eniyi'], 'g-', label='En İyi Sabit Konum')
    if 'enerji_wh_ozel_sabit' in monthly_data.columns and not monthly_data['enerji_wh_ozel_sabit'].equals(monthly_data['enerji_wh_sabit_eniyi']):
        ax.plot(monthly_data.index, monthly_data['enerji_wh_ozel_sabit'], 'r-', label='Özel Sabit Konum')
    ax.set_ylabel('Enerji Üretimi (kWh/ay)')
    ax.set_title(f'{location_name} için Aylık Enerji Üretimi')
    ax.set_xlabel('Ay')
    ax.legend()
    ax.grid(True)
    plt.xticks(rotation=45)
    fig_monthly.tight_layout()
    visualizations['monthly'] = fig_monthly
    
    # 2. Karşılaştırmalı toplam enerji grafiği (çubuk grafik)
    fig_total = plt.figure(figsize=(8, 6))
    ax_total = fig_total.add_subplot(1, 1, 1)
    total_data = {
        'İzleme': monthly_data['enerji_wh_izleme'].sum(),
        'En İyi Sabit': monthly_data['enerji_wh_sabit_eniyi'].sum()
    }
    if 'enerji_wh_ozel_sabit' in monthly_data.columns and not monthly_data['enerji_wh_ozel_sabit'].equals(monthly_data['enerji_wh_sabit_eniyi']):
        total_data['Özel Sabit'] = monthly_data['enerji_wh_ozel_sabit'].sum()
    colors = ['blue', 'green', 'red']
    bars = ax_total.bar(total_data.keys(), total_data.values(), color=colors[:len(total_data)])
    for bar in bars:
        height = bar.get_height()
        ax_total.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{height:.1f}',
                ha='center', va='bottom', rotation=0)
    ax_total.set_ylabel('Toplam Enerji Üretimi (kWh/yıl)')
    ax_total.set_title(f'{location_name} için Yıllık Toplam Enerji Üretimi')
    ax_total.grid(axis='y')
    fig_total.tight_layout()
    visualizations['total'] = fig_total
    
    # 3. Verim karşılaştırma grafiği (çubuk grafik)
    fig_efficiency = plt.figure(figsize=(8, 6))
    ax_eff = fig_efficiency.add_subplot(1, 1, 1)
    tracking_energy = monthly_data['enerji_wh_izleme'].sum()
    optimal_energy = monthly_data['enerji_wh_sabit_eniyi'].sum()
    efficiency_data = {
        'En İyi Sabit': (optimal_energy / tracking_energy) * 100
    }
    if 'enerji_wh_ozel_sabit' in monthly_data.columns and not monthly_data['enerji_wh_ozel_sabit'].equals(monthly_data['enerji_wh_sabit_eniyi']):
        custom_energy = monthly_data['enerji_wh_ozel_sabit'].sum()
        efficiency_data['Özel Sabit'] = (custom_energy / tracking_energy) * 100
    eff_bars = ax_eff.bar(efficiency_data.keys(), efficiency_data.values(), color=['green', 'red'][:len(efficiency_data)])
    for bar in eff_bars:
        height = bar.get_height()
        ax_eff.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{height:.1f}%',
                ha='center', va='bottom', rotation=0)
    ax_eff.set_ylabel('İzleme Sistemine Göre Verimlilik (%)')
    ax_eff.set_title(f'{location_name} için Sabit Sistemlerin İzleme Sistemine Göre Verimliliği')
    ax_eff.set_ylim(0, 105)
    ax_eff.grid(axis='y')
    fig_efficiency.tight_layout()
    visualizations['efficiency'] = fig_efficiency
    
    # 4. Eğim açılarını gösteren görsel (panel konumu)
    fig_tilt = plt.figure(figsize=(8, 6))
    ax_tilt = fig_tilt.add_subplot(1, 1, 1, projection='3d')
    def plot_panel(ax, ew_tilt, ns_tilt, color, label):
        normal = get_panel_normal(ew_tilt, ns_tilt)
        center = np.array([0, 0, 0])
        width, height = 0.5, 0.5
        corners_flat = np.array([
            [-width, -height, 0],
            [width, -height, 0],
            [width, height, 0],
            [-width, height, 0],
            [-width, -height, 0]
        ])
        def rotation_matrix_x(angle_rad):
            return np.array([
                [1, 0, 0],
                [0, np.cos(angle_rad), -np.sin(angle_rad)],
                [0, np.sin(angle_rad), np.cos(angle_rad)]
            ])
        def rotation_matrix_y(angle_rad):
            return np.array([
                [np.cos(angle_rad), 0, np.sin(angle_rad)],
                [0, 1, 0],
                [-np.sin(angle_rad), 0, np.cos(angle_rad)]
            ])
        Ry = rotation_matrix_y(np.radians(ew_tilt))
        Rx = rotation_matrix_x(np.radians(ns_tilt))
        corners = np.zeros_like(corners_flat)
        for i, corner in enumerate(corners_flat):
            rotated = Ry @ corner
            rotated = Rx @ rotated
            corners[i] = rotated
        ax.plot(corners[:, 0], corners[:, 1], corners[:, 2], color=color, label=label)
        ax.quiver(0, 0, 0, normal[0], normal[1], normal[2], color=color, arrow_length_ratio=0.1, length=0.8)
    plot_panel(ax_tilt, best_ew_tilt, best_ns_tilt, 'green', f'En İyi Sabit Konum ({best_ew_tilt}°, {best_ns_tilt}°)')
    if custom_ew_tilt is not None and custom_ns_tilt is not None:
        plot_panel(ax_tilt, custom_ew_tilt, custom_ns_tilt, 'red', f'Özel Sabit Konum ({custom_ew_tilt}°, {custom_ns_tilt}°)')
    plot_panel(ax_tilt, 0, 0, 'blue', 'Yatay Panel (0°, 0°)')
    ax_tilt.quiver(0, 0, 0, 1, 0, 0, color='gray', arrow_length_ratio=0.1, length=0.7)
    ax_tilt.quiver(0, 0, 0, 0, 1, 0, color='gray', arrow_length_ratio=0.1, length=0.7)
    ax_tilt.quiver(0, 0, 0, 0, 0, 1, color='gray', arrow_length_ratio=0.1, length=0.7)
    ax_tilt.set_xlabel('Doğu (+) / Batı (-)')
    ax_tilt.set_ylabel('Kuzey (+) / Güney (-)')
    ax_tilt.set_zlabel('Yukarı')
    max_range = 1.0
    ax_tilt.set_xlim(-max_range, max_range)
    ax_tilt.set_ylim(-max_range, max_range)
    ax_tilt.set_zlim(-max_range, max_range)
    ax_tilt.set_title(f'{location_name} için Panel Konumları')
    ax_tilt.legend()
    fig_tilt.tight_layout()
    visualizations['tilt'] = fig_tilt
    
    return visualizations

def calculate_and_export(locations_data, start_year, panel_efficiency_decimal, custom_ew_tilt, custom_ns_tilt, filepath):
    """Hesaplamaları yapar ve sonuçları Excel'e dışa aktarır."""
    if not filepath:
        messagebox.showerror("Hata", "Kayıt dosya yolu belirtilmedi.")
        return
    
    if not (0 < panel_efficiency_decimal <= 1.0):
        messagebox.showerror("Girdi Hatası", "Panel verimliliği %0 ile %100 arasında olmalıdır.")
        return
    
    try:
        tum_sonuclar = {}
        tum_aylik_veriler = {}
        tum_grafikler = {}
        
        for loc_data in locations_data:
            print(f"{loc_data['name']} işleniyor...")
            
            vectors_df = calculate_solar_vectors(loc_data, start_year)
            
            tracking_energy_df = calculate_energy(vectors_df, panel_efficiency_decimal)
            tracking_energy_df.rename(columns={'enerji_wh': 'enerji_wh_izleme'}, inplace=True)
            
            best_ew_tilt, best_ns_tilt = find_best_fixed_position(vectors_df, panel_efficiency_decimal)
            optimal_energy_df = calculate_energy(vectors_df, panel_efficiency_decimal, best_ew_tilt, best_ns_tilt)
            optimal_energy_df.rename(columns={'enerji_wh': 'enerji_wh_sabit_eniyi'}, inplace=True)
            
            if custom_ew_tilt is not None and custom_ns_tilt is not None:
                custom_energy_df = calculate_energy(vectors_df, panel_efficiency_decimal, custom_ew_tilt, custom_ns_tilt)
                custom_energy_df.rename(columns={'enerji_wh': 'enerji_wh_ozel_sabit'}, inplace=True)
            else:
                custom_energy_df = optimal_energy_df.rename(columns={'enerji_wh_sabit_eniyi': 'enerji_wh_ozel_sabit'})
            
            combined_df = pd.concat([tracking_energy_df, optimal_energy_df, custom_energy_df], axis=1)
            monthly_data = combined_df.resample('ME').sum() / 1000
            monthly_data.index = monthly_data.index.strftime('%Y-%m')
            
            tum_aylik_veriler[loc_data['name']] = monthly_data
            tum_sonuclar[loc_data['name']] = {
                'aylik_veriler': monthly_data,
                'eniyi_dogu_bati_egimi': best_ew_tilt,
                'eniyi_kuzey_guney_egimi': best_ns_tilt,
                'toplam_enerji_izleme': monthly_data['enerji_wh_izleme'].sum(),
                'toplam_enerji_sabit_eniyi': monthly_data['enerji_wh_sabit_eniyi'].sum(),
                'toplam_enerji_ozel_sabit': monthly_data['enerji_wh_ozel_sabit'].sum()
            }
            
            visualizations = create_visualizations(
                loc_data['name'], monthly_data, best_ew_tilt, best_ns_tilt, custom_ew_tilt, custom_ns_tilt
            )
            tum_grafikler[loc_data['name']] = visualizations
            
            for vis_name, fig in visualizations.items():
                fig_filepath = f"{os.path.splitext(filepath)[0]}_{loc_data['name']}_{vis_name}.png"
                fig.savefig(fig_filepath)
                plt.close(fig)
        
        ozet_veriler = []
        for name, results in tum_sonuclar.items():
            ozet_veriler.append({
                'Konum': name,
                'En İyi Doğu-Batı Eğimi (derece)': results['eniyi_dogu_bati_egimi'],
                'En İyi Kuzey-Güney Eğimi (derece)': results['eniyi_kuzey_guney_egimi'],
                'Toplam Enerji - İzleme (kWh/yıl)': results['toplam_enerji_izleme'],
                'Toplam Enerji - En İyi Sabit (kWh/yıl)': results['toplam_enerji_sabit_eniyi'],
                'Toplam Enerji - Özel Sabit (kWh/yıl)': results['toplam_enerji_ozel_sabit']
            })
        
        ozet_df = pd.DataFrame(ozet_veriler)
        
        birlesik_aylik_veriler = {}
        for name, monthly_df in tum_aylik_veriler.items():
            for col in monthly_df.columns:
                birlesik_aylik_veriler[f"{name}_{col}"] = monthly_df[col]
        
        birlesik_aylik_df = pd.DataFrame(birlesik_aylik_veriler)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            ozet_df.to_excel(writer, sheet_name='Özet', index=False)
            birlesik_aylik_df.to_excel(writer, sheet_name='Aylık Veriler')
            bilgi_verileri = pd.DataFrame({
                'Sütun': [
                    'enerji_wh_izleme', 'enerji_wh_sabit_eniyi', 'enerji_wh_ozel_sabit'
                ],
                'Açıklama': [
                    'Her zaman güneşe dik olan panelin aylık enerji üretimi (kWh)',
                    'En iyi sabit Doğu-Batı ve Kuzey-Güney eğim açılarında panelin aylık enerji üretimi (kWh)',
                    'Kullanıcı tarafından belirtilen sabit Doğu-Batı ve Kuzey-Güney eğim açılarında panelin aylık enerji üretimi (kWh)'
                ]
            })
            bilgi_verileri.to_excel(writer, sheet_name='Bilgi', index=False)
        
        messagebox.showinfo("Başarılı",
                           f"Enerji üretim verileri şuraya kaydedildi:\n"
                           f"{filepath}\n\n"
                           f"Görsel grafikler şuraya kaydedildi:\n"
                           f"{os.path.splitext(filepath)[0]}_[KONUM]_[VIS_TYPE].png\n\n"
                           f"Not: Bu, açık gökyüzünde koşullarında 1m² panel için potansiyel değerleri temsil eder.")
        
        if tum_grafikler:
            return tum_grafikler[list(tum_grafikler.keys())[0]]['monthly']
        
    except Exception as e:
        messagebox.showerror("Hata", f"Beklenmedik bir hata oluştu:\n{e}")
        import traceback
        traceback.print_exc()
        return None

class SolarTiltPowerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SunC - Güneş Paneli Pozisyon ve Elektrik Üretim Simülatörü")
        self.root.geometry("800x700")
        
        self.input_frame = ttk.LabelFrame(root, text="Girdiler", padding=(10, 5))
        self.input_frame.pack(padx=10, pady=10, fill="x")
        
        self.tz_display_options = []
        self.tz_value_map = {}
        for offset in range(-12, 15):
            display = f"GMT{offset:+d}"
            value = f"Etc/GMT{-offset:+d}"
            self.tz_display_options.append(display)
            self.tz_value_map[display] = value
        
        self.default_tz_display = "GMT+3"
        
        self.locations_entries = []
        self.add_location_fields()
        
        config_frame = ttk.Frame(self.input_frame)
        config_frame.pack(fill="x", pady=5, padx=5)
        
        ttk.Label(config_frame, text="Başlangıç Yılı:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.year_entry = ttk.Entry(config_frame, width=8)
        self.year_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        current_year = datetime.datetime.now().year
        self.year_entry.insert(0, str(current_year))
        
        ttk.Label(config_frame, text="Panel Verimliliği (%):").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.efficiency_entry = ttk.Entry(config_frame, width=6)
        self.efficiency_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        self.efficiency_entry.insert(0, "20")
        
        self.custom_position_var = tk.BooleanVar()
        self.custom_position_check = ttk.Checkbutton(
            config_frame,
            text="Özel Panel Konumu",
            variable=self.custom_position_var,
            command=self.toggle_custom_position
        )
        self.custom_position_check.grid(row=1, column=0, columnspan=4, sticky="w", padx=5, pady=2)
        
        self.custom_angle_frame = ttk.Frame(config_frame)
        self.custom_angle_frame.grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=2)
        
        ttk.Label(self.custom_angle_frame, text="Doğu-Batı Eğimi (°):").grid(row=0, column=0, sticky="w", padx=5)
        self.ew_tilt_entry = ttk.Entry(self.custom_angle_frame, width=6)
        self.ew_tilt_entry.grid(row=0, column=1, sticky="w", padx=5)
        self.ew_tilt_entry.insert(0, "0")
        
        ttk.Label(self.custom_angle_frame, text="Kuzey-Güney Eğimi (°):").grid(row=0, column=2, sticky="w", padx=5)
        self.ns_tilt_entry = ttk.Entry(self.custom_angle_frame, width=6)
        self.ns_tilt_entry.grid(row=0, column=3, sticky="w", padx=5)
        self.ns_tilt_entry.insert(0, "0")
        
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(2, weight=1)
        self.custom_angle_frame.columnconfigure(0, weight=0)
        self.custom_angle_frame.columnconfigure(2, weight=0)
        
        self.toggle_custom_position()
        
        # Button frame for Calculate and Reset buttons
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(padx=10, pady=10)
        
        calculate_button = ttk.Button(
            self.button_frame,
            text="Hesapla ve Verileri Dışa Aktar",
            command=self.on_calculate_click
        )
        calculate_button.pack(side=tk.LEFT, padx=5)
        
        reset_button = ttk.Button(
            self.button_frame,
            text="Sıfırla",
            command=self.reset_inputs
        )
        reset_button.pack(side=tk.LEFT, padx=5)
        
        self.plot_frame = ttk.LabelFrame(root, text="Grafik", padding=(10, 5))
        self.plot_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        help_text = ("Bu program,verilen konumda 1m² güneş paneli için enerji üretimini hesaplar.\n"
                     "Panel, Doğu-Batı ve Kuzey-Güney eksenlerinde güneşi takip edebilir veya sabit bir konumda kalabilir.\n"
                     "Sonuçlar aylık bazda Excel dosyasına kaydedilir.")
        help_label = ttk.Label(root, text=help_text, wraplength=780, justify=tk.CENTER)
        help_label.pack(padx=10, pady=5)
        
        self.canvas = None
    
    def add_location_fields(self):
        loc_frame = ttk.Frame(self.input_frame)
        loc_frame.pack(fill="x", pady=5)
        ttk.Label(loc_frame, text="Konum:").grid(row=0, column=0, columnspan=4, sticky="w", padx=5)
        
        ttk.Label(loc_frame, text="İsim:").grid(row=1, column=0, sticky="w", padx=5)
        name_entry = ttk.Entry(loc_frame, width=15)
        name_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5)
        
        ttk.Label(loc_frame, text="Enlem (°):").grid(row=2, column=0, sticky="w", padx=5)
        lat_entry = ttk.Entry(loc_frame, width=10)
        lat_entry.grid(row=2, column=1, sticky="ew", padx=5)
        
        ttk.Label(loc_frame, text="Boylam (°):").grid(row=2, column=2, sticky="w", padx=5)
        lon_entry = ttk.Entry(loc_frame, width=10)
        lon_entry.grid(row=2, column=3, sticky="ew", padx=5)
        
        ttk.Label(loc_frame, text="Saat Dilimi:").grid(row=3, column=0, sticky="w", padx=5)
        tz_combo = ttk.Combobox(loc_frame, values=self.tz_display_options, state="readonly", width=10)
        tz_combo.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5)
        tz_combo.set(self.default_tz_display)
        
        loc_frame.columnconfigure(1, weight=1)
        loc_frame.columnconfigure(3, weight=1)
        
        entry_dict = {'name': name_entry, 'lat': lat_entry, 'lon': lon_entry, 'tz_combo': tz_combo}
        self.locations_entries.append(entry_dict)
        return entry_dict
    
    def toggle_custom_position(self):
        state = 'normal' if self.custom_position_var.get() else 'disabled'
        self.ew_tilt_entry.config(state=state)
        self.ns_tilt_entry.config(state=state)
    
    def reset_inputs(self):
        """Clear all input fields and reset to initial state."""
        # Clear plot if exists
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        
        # Clear fields in the location
        loc = self.locations_entries[0]
        loc['name'].delete(0, tk.END)
        loc['lat'].delete(0, tk.END)
        loc['lon'].delete(0, tk.END)
        loc['tz_combo'].set(self.default_tz_display)
        
        # Reset year and efficiency
        current_year = datetime.datetime.now().year
        self.year_entry.delete(0, tk.END)
        self.year_entry.insert(0, str(current_year))
        self.efficiency_entry.delete(0, tk.END)
        self.efficiency_entry.insert(0, "20")
        
        # Reset custom position
        self.custom_position_var.set(False)
        self.ew_tilt_entry.delete(0, tk.END)
        self.ew_tilt_entry.insert(0, "0")
        self.ns_tilt_entry.delete(0, tk.END)
        self.ns_tilt_entry.insert(0, "0")
        self.toggle_custom_position()
    
    def display_plot(self, fig):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def on_calculate_click(self):
        locations_data = []
        try:
            start_year = int(self.year_entry.get())
            efficiency_percent = float(self.efficiency_entry.get())
            
            if not (0 < efficiency_percent <= 100):
                raise ValueError("Panel Verimliliği %0 ile %100 arasında olmalıdır.")
            panel_efficiency_decimal = efficiency_percent / 100.0
            
            if start_year < 1950 or start_year > 2100:
                raise ValueError("Yıl 1950 ile 2100 arasında olmalıdır")
            
            custom_ew_tilt = None
            custom_ns_tilt = None
            if self.custom_position_var.get():
                try:
                    custom_ew_tilt = float(self.ew_tilt_entry.get())
                    custom_ns_tilt = float(self.ns_tilt_entry.get())
                    if not (-90 <= custom_ew_tilt <= 90):
                        raise ValueError("Doğu-Batı eğim açısı -90° ile 90° arasında olmalıdır.")
                    if not (-90 <= custom_ns_tilt <= 90):
                        raise ValueError("Kuzey-Güney eğim açısı -90° ile 90° arasında olmalıdır.")
                except ValueError as ve:
                    messagebox.showerror("Girdi Hatası", f"Özel eğim açıları için geçerli sayılar girin.\nDetaylar: {ve}")
                    return
            
            entries = self.locations_entries[0]
            name = entries['name'].get().strip()
            lat_str = entries['lat'].get()
            lon_str = entries['lon'].get()
            selected_display_tz = entries['tz_combo'].get()
            
            if not all([name, lat_str, lon_str, selected_display_tz]):
                messagebox.showerror("Girdi Hatası", "Lütfen tüm alanları doldurun.")
                return
            
            try:
                tz_value = self.tz_value_map[selected_display_tz]
            except KeyError:
                messagebox.showerror("Girdi Hatası", "Geçersiz saat dilimi seçildi.")
                return
            
            locations_data.append({
                'name': name,
                'latitude': float(lat_str),
                'longitude': float(lon_str),
                'timezone': tz_value
            })
            
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel dosyaları", "*.xlsx"), ("Tüm dosyalar", "*.*")],
                title="Enerji Verisini Farklı Kaydet..."
            )
            
            if save_path:
                fig = calculate_and_export(
                    locations_data,
                    start_year,
                    panel_efficiency_decimal,
                    custom_ew_tilt,
                    custom_ns_tilt,
                    save_path
                )
                
                if fig:
                    self.display_plot(fig)
            else:
                print("Kaydetme işlemi iptal edildi.")
        
        except ValueError as ve:
            messagebox.showerror("Girdi Hatası", f"Lütfen Yıl, Verimlilik, Enlem ve Boylam için geçerli sayılar girin.\nDetaylar: {ve}")
        except Exception as e:
            messagebox.showerror("Hata", f"Girdi işlenirken beklenmedik bir hata oluştu:\n{e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    root = tk.Tk()
    app = SolarTiltPowerApp(root)
    root.mainloop()