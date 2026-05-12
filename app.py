import streamlit as st
import xml.etree.ElementTree as ET
import re

# Sayfa ayarları
st.set_page_config(page_title="XML Sync Tool v5", layout="wide")

# --- SABİT MPWO ŞABLONU ---
MPWO_SABLON = """<WorkOrderResponse>
    <Header>
        <activityName>Installation</activityName>
        <msgName>ManagePartnerWorkOrderResponse</msgName>
        <msgType>RESPONSE</msgType>
        <senderURI>ATTIP</senderURI>
        <destinationURI>CW</destinationURI>
        <activityStatus>SUCCESS</activityStatus>
        <priority>4</priority>
        <userid>IYS</userid>
        <timestamp>BEKLIYOR</timestamp>
        <service>ManagePartnerWorkOrder</service>
        <correlationID>BEKLIYOR</correlationID>
        <businessID>BEKLIYOR</businessID>
        <conversationID>BEKLIYOR</conversationID>
        <requestID>BEKLIYOR</requestID>
        <messageID>BEKLIYOR</messageID>
    </Header>
    <Body>
        <workOrderResponse>
            <orderInfo workOrderId="BEKLIYOR" serviceOrderId="BEKLIYOR" actualCompletionDate="BEKLIYOR" notes="-" resultCode="OK">
                <fieldSupportAvailability/>
                <fieldSupportUnavailabilityReason/>
            </orderInfo>
            <cpeInfo cpeSubscriptionID="BEKLIYOR" cpeEquipmentTypeCode="BEKLIYOR" cpeEquipmentTypeName="BEKLIYOR" cpeEquipmentModelCode="BEKLIYOR" cpeEquipmentModelName="BEKLIYOR" cpeVendorCode="BEKLIYOR" cpeVendorName="BEKLIYOR" cpeSerialNumber="BEKLIYOR" cpeMacAddress="" isCpeEquipmentReturned="" managementType="" managementIp="" isCpeChanged=""/>
        </workOrderResponse>
    </Body>
</WorkOrderResponse>"""

def get_cvalue(root, key_name, ns):
    """Log içindeki ns13:cValue etiketlerini bulur."""
    node = root.find(f".//ns13:cValue[@key='{key_name}']", ns)
    return node.text if node is not None and node.text is not None else ""

st.title("🚀 XML Sync Tool - Web Dashboard")
st.info("Kaynak 1'den ID ve Timestamp'ler, Kaynak 2'den teknik detaylar alınarak şablon doldurulur.")

# Arayüz Kutuları
col1, col2 = st.columns(2)

with col1:
    raw1 = st.text_area("Kaynak 1 (İlk Mesaj - Request XML)", height=300, placeholder="Request XML buraya...")

with col2:
    raw2 = st.text_area("Kaynak 2 (Log / Exception Mesajı)", height=300, placeholder="Exception ve XML bloğu buraya...")

# İşlem Butonu
if st.button("🔄 XML'i Senkronize Et ve Oluştur", use_container_width=True):
    if not raw1 or not raw2:
        st.warning("Lütfen her iki kutuya da veri yapıştırın.")
    else:
        try:
            # 1. Namespaceler
            ns2 = {'ns13': 'http://www.innova.com.tr/WFM'}

            # Kaynak 1'i Parse Et
            root_req = ET.fromstring(raw1)
            
            # Kaynak 2 (Log) içinden XML'i ayıkla
            xml_match = re.search(r'<ns13:genericIYSMessageRequest.*</ns13:genericIYSMessageRequest>', raw2, re.DOTALL)
            if not xml_match:
                st.error("Kaynak 2 (Log) içerisinde geçerli bir XML bloğu bulunamadı!")
            else:
                root_log = ET.fromstring(xml_match.group(0))
                root_res = ET.fromstring(MPWO_SABLON)

                # Şablondaki kritik düğümleri en başta tanımlayalım (Hata almamak için)
                order_info_res = root_res.find(".//orderInfo")
                cpe_info_res = root_res.find(".//cpeInfo")

                # --- KAYNAK 1 (REQUEST) İŞLEMLERİ ---
                # A. Header ID'ler (Wildcard {*} ile tüm namespace varyasyonlarını yakalar)
                id_list = ["correlationID", "businessID", "conversationID", "requestID", "messageID"]
                for id_name in id_list:
                    val_node = root_req.find(f".//{{*}}{id_name}")
                    if val_node is not None:
                        target = root_res.find(f".//{{*}}{id_name}") # Şablonda ara
                        if target is not None:
                            target.text = val_node.text

                # B. Timestamp
                ts_node = root_req.find(".//{{*}}timestamp")
                if ts_node is not None:
                    target_ts = root_res.find(".//Header/timestamp")
                    if target_ts is not None: target_ts.text = ts_node.text

                # C. orderInfo Attributes (ID'ler)
                order_info_req = root_req.find(".//{{*}}orderInfo")
                if order_info_req is not None and order_info_res is not None:
                    order_info_res.set("workOrderId", order_info_req.attrib.get("workOrderId", "BEKLIYOR"))
                    order_info_res.set("serviceOrderId", order_info_req.attrib.get("serviceOrderId", "BEKLIYOR"))

                # D. cpeSubscriptionID
                # Önce ilk mesajdaki attribute'a bak, yoksa id tag'ine bak
                cpe_req = root_req.find(".//{{*}}cpeInfo")
                if cpe_req is not None and "cpeSubscriptionID" in cpe_req.attrib:
                    cpe_info_res.set("cpeSubscriptionID", cpe_req.attrib["cpeSubscriptionID"])
                else:
                    alt_sub_id = root_req.findtext(".//{{*}}id")
                    if alt_sub_id: cpe_info_res.set("cpeSubscriptionID", alt_sub_id)


                # --- KAYNAK 2 (LOG) İŞLEMLERİ ---
                # E. Actual Date
                actual_date = root_log.findtext(".//ns13:actualEndDate", "", ns2)
                if actual_date and order_info_res is not None:
                    order_info_res.set("actualCompletionDate", actual_date.replace(" ", "T"))

                # F. CPE Detayları (Log içindeki resource altından)
                log_resource = root_log.find(".//ns13:resource", ns2)
                if log_resource is not None and cpe_info_res is not None:
                    cpe_mapping = {
                        "cpeEquipmentTypeCode": "TIP_KODU",
                        "cpeEquipmentTypeName": "TIP_ADI",
                        "cpeEquipmentModelCode": "MODEL_KODU",
                        "cpeEquipmentModelName": "MODEL_ADI",
                        "cpeVendorCode": "MARKA_KODU",
                        "cpeVendorName": "MARKA_ADI",
                        "cpeSerialNumber": "SERI_NO"
                    }
                    for sab_attr, log_key in cpe_mapping.items():
                        val = get_cvalue(log_resource, log_key, ns2)
                        if val: cpe_info_res.set(sab_attr, val)

                # --- SONUÇ GÖSTERİMİ ---
                final_xml = ET.tostring(root_res, encoding='unicode')
                st.divider()
                st.subheader("✅ Düzenlenmiş XML Sonucu")
                st.code(final_xml, language='xml')
                st.balloons()

        except Exception as e:
            st.error(f"Sistemsel bir hata oluştu: {e}")