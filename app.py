import streamlit as st
import xml.etree.ElementTree as ET
import re

# ... (Şablon kısmı aynı kalacak) ...

if st.button("🔄 XML'i Senkronize Et ve Oluştur", use_container_width=True):
    if not raw1 or not raw2:
        st.warning("Lütfen her iki kutuya da veri yapıştırın.")
    else:
        try:
            # 1. Namespaceler
            ns2 = {'ns13': 'http://www.innova.com.tr/WFM'}
            root_req = ET.fromstring(raw1)
            
            xml_match = re.search(r'<ns13:genericIYSMessageRequest.*</ns13:genericIYSMessageRequest>', raw2, re.DOTALL)
            if not xml_match:
                st.error("Kaynak 2 (Log) içerisinde geçerli bir XML bloğu bulunamadı!")
            else:
                root_log = ET.fromstring(xml_match.group(0))
                root_res = ET.fromstring(MPWO_SABLON)

                order_info_res = root_res.find(".//orderInfo")
                cpe_info_res = root_res.find(".//cpeInfo")

                # --- KAYNAK 1 (REQUEST) İŞLEMLERİ ---
                # A. Header ID'ler
                id_list = ["correlationID", "businessID", "conversationID", "requestID", "messageID"]
                for id_name in id_list:
                    val_node = root_req.find(f".//{{*}}{id_name}")
                    if val_node is not None:
                        target = root_res.find(f".//Header/{id_name}")
                        if target is not None: target.text = val_node.text

                # B. TIMESTAMP (Özel kontrol)
                # Hem tag içeriğine hem de farklı derinliklere bakıyoruz
                ts_node = root_req.find(".//{*}timestamp")
                if ts_node is not None:
                    root_res.find(".//Header/timestamp").text = ts_node.text

                # C. orderInfo Attributes (workOrderId & serviceOrderId)
                order_info_req = root_req.find(".//{*}orderInfo")
                if order_info_req is not None and order_info_res is not None:
                    order_info_res.set("workOrderId", order_info_req.attrib.get("workOrderId", "BEKLIYOR"))
                    order_info_res.set("serviceOrderId", order_info_req.attrib.get("serviceOrderId", "BEKLIYOR"))

                # D. cpeSubscriptionID (Gelişmiş Arama)
                # 1. Yol: cpeInfo özniteliği olarak ara
                cpe_req_attr = root_req.find(".//{*}cpeInfo")
                found_sub_id = None
                
                if cpe_req_attr is not None and "cpeSubscriptionID" in cpe_req_attr.attrib:
                    found_sub_id = cpe_req_attr.attrib["cpeSubscriptionID"]
                
                # 2. Yol: Eğer hala bulunamadıysa tag olarak ara (Örn: <subscriptionId>)
                if not found_sub_id:
                    found_sub_id = root_req.findtext(".//{*}subscriptionId")
                
                # 3. Yol: Kaynak 1 içindeki tüm resource id'lerine bak
                if not found_sub_id:
                    found_sub_id = root_req.findtext(".//{*}id")

                if found_sub_id and cpe_info_res is not None:
                    cpe_info_res.set("cpeSubscriptionID", found_sub_id)


                # --- KAYNAK 2 (LOG) İŞLEMLERİ ---
                # E. Actual Date
                actual_date = root_log.findtext(".//ns13:actualEndDate", "", ns2)
                if actual_date and order_info_res is not None:
                    order_info_res.set("actualCompletionDate", actual_date.replace(" ", "T"))

                # F. CPE Detayları
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

                # Sonuç
                final_xml = ET.tostring(root_res, encoding='unicode')
                st.code(final_xml, language='xml')

        except Exception as e:
            st.error(f"Hata: {e}")