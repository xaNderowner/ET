import streamlit as st
import xml.etree.ElementTree as ET
import re

# Sayfa Konfigürasyonu
st.set_page_config(page_title="XML ID & Attribute Sync Tool", layout="wide")

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
    node = root.find(f".//ns13:cValue[@key='{key_name}']", ns)
    return node.text if node is not None and node.text is not None else ""

# --- Arayüz ---
st.title("🚀 XML ID & Attribute Sync Tool")
st.markdown("Verileri yapıştırın ve anında güncel XML sonucunu alın.")

# Dropbox
msg_type = st.selectbox("Mesaj Türü Seçin", ["MPWO", "Asup_Termination", "DSL_Termination"])

col1, col2 = st.columns(2)

with col1:
    raw1 = st.text_area("Kaynak 1 (İlk Mesaj - Request XML)", height=300)

with col2:
    raw2 = st.text_area("Kaynak 2 (Log/Exception XML)", height=300)

if st.button("🔄 XML'i Oluştur", use_container_width=True):
    if raw1 and raw2:
        try:
            # Namespaceler
            ns1 = {
                'esbCommonType': 'http://www.turktelekom.com.tr/aTTIP/Common/CommonType/1.0',
                'woReq': 'http://www.turktelekom.com.tr/aTTIP/Services/OrderFulfillment/ManagePartnerWorkOrder/WorkOrderRequest/1.0'
            }
            ns2 = {'ns13': 'http://www.innova.com.tr/WFM'}

            # Log ayıklama
            xml_match = re.search(r'<ns13:genericIYSMessageRequest.*</ns13:genericIYSMessageRequest>', raw2, re.DOTALL)
            if not xml_match:
                st.error("Kaynak 2'de geçerli XML bloğu bulunamadı!")
            else:
                root_req = ET.fromstring(raw1)
                root_log = ET.fromstring(xml_match.group(0))
                root_res = ET.fromstring(MPWO_SABLON)

                if msg_type == "MPWO":
                    # 1. Header ID'ler ve Timestamp
                    id_list = ["correlationID", "businessID", "conversationID", "requestID", "messageID"]
                    for id_name in id_list:
                        val = root_req.find(f".//esbCommonType:{id_name}", ns1)
                        if val is not None: root_res.find(f".//Header/{id_name}").text = val.text
                    
                    ts_val = root_req.find(".//esbCommonType:timestamp", ns1)
                    if ts_val is not None: root_res.find(".//Header/timestamp").text = ts_val.text

                    # 2. orderInfo
                    order_info_res = root_res.find(".//orderInfo")
                    req_order = root_req.find(".//woReq:orderInfo", ns1)
                    if req_order is not None:
                        order_info_res.set("workOrderId", req_order.attrib.get("workOrderId", ""))
                        order_info_res.set("serviceOrderId", req_order.attrib.get("serviceOrderId", ""))
                    
                    actual_date = root_log.findtext(".//ns13:actualEndDate", "", ns2)
                    if actual_date: order_info_res.set("actualCompletionDate", actual_date.replace(" ", "T"))

                    # 3. cpeInfo
                    cpe_info_res = root_res.find(".//cpeInfo")
                    req_cpe_info = root_req.find(".//woReq:cpeInfo", ns1)
                    if req_cpe_info is not None:
                        sub_id = req_cpe_info.attrib.get("cpeSubscriptionID", "")
                        if sub_id: cpe_info_res.set("cpeSubscriptionID", sub_id)
                    else:
                        alt_sub_id = root_req.findtext(".//woReq:resource/woReq:id", "", ns1)
                        if alt_sub_id: cpe_info_res.set("cpeSubscriptionID", alt_sub_id)

                    # Log'dan detaylar
                    log_resource = root_log.find(".//ns13:resource", ns2)
                    if log_resource is not None:
                        cpe_mapping = {
                            "cpeEquipmentTypeCode": "TIP_KODU", "cpeEquipmentTypeName": "TIP_ADI",
                            "cpeEquipmentModelCode": "MODEL_KODU", "cpeEquipmentModelName": "MODEL_ADI",
                            "cpeVendorCode": "MARKA_KODU", "cpeVendorName": "MARKA_ADI", "cpeSerialNumber": "SERI_NO"
                        }
                        for sab_attr, log_key in cpe_mapping.items():
                            val = get_cvalue(log_resource, log_key, ns2)
                            if val: cpe_info_res.set(sab_attr, val)

                # Sonuç Gösterimi
                final_xml = ET.tostring(root_res, encoding='unicode')
                st.subheader("Sonuç XML")
                st.code(final_xml, language='xml')
                st.success("XML Başarıyla Oluşturuldu! Yukarıdaki kutudan kopyalayabilirsiniz.")
        
        except Exception as e:
            st.error(f"Hata: {e}")
    else:
        st.warning("Lütfen her iki kutuya da veri yapıştırın.")