import streamlit as st
import xml.etree.ElementTree as ET
import re

st.set_page_config(page_title="XML Sync Tool", layout="wide")

# --- ŞABLON ---
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

st.title("🚀 XML Sync Tool (Web Version)")

raw1 = st.text_area("Kaynak 1 (Request XML)", height=250)
raw2 = st.text_area("Kaynak 2 (Log XML)", height=250)

if st.button("🔄 XML'i Oluştur", use_container_width=True):
    if raw1 and raw2:
        try:
            # 1. NAMESPACE TANIMLARI (Çok kritik)
            # Kaynak 1 için geniş bir tanımlama yapıyoruz
            ns1 = {
                'esbCommonType': 'http://www.turktelekom.com.tr/aTTIP/Common/CommonType/1.0',
                'esbCommon': 'http://www.turktelekom.com.tr/aTTIP/Common/1.0',
                'woReq': 'http://www.turktelekom.com.tr/aTTIP/Services/OrderFulfillment/ManagePartnerWorkOrder/WorkOrderRequest/1.0',
                'attipCDM': 'http://www.turktelekom.com.tr/aTTIP/CDM/1.0'
            }
            ns2 = {'ns13': 'http://www.innova.com.tr/WFM'}

            # Kaynak 1'i parse et
            root_req = ET.fromstring(raw1)
            
            # Kaynak 2 (Log) içinden XML'i ayıkla
            xml_match = re.search(r'<ns13:genericIYSMessageRequest.*</ns13:genericIYSMessageRequest>', raw2, re.DOTALL)
            if not xml_match:
                st.error("Kaynak 2'de XML bloğu bulunamadı!")
            else:
                root_log = ET.fromstring(xml_match.group(0))
                root_res = ET.fromstring(MPWO_SABLON)

                # --- KAYNAK 1 (REQUEST) İŞLEMLERİ ---
                # 1. Header ID'ler
                id_list = ["correlationID", "businessID", "conversationID", "requestID", "messageID"]
                for id_name in id_list:
                    # Bazı XML'lerde 'esbCommonType' bazılarında 'ns7' olabilir. 
                    # '{*}tagname' kullanarak namespace ne olursa olsun sadece tag adına odaklanıyoruz.
                    val_node = root_req.find(f".//{{*}}{id_name}")
                    if val_node is not None:
                        target = root_res.find(f".//Header/{id_name}")
                        if target is not None: target.text = val_node.text

                # 2. Timestamp
                ts_node = root_req.find(".//{*}timestamp")
                if ts_node is not None:
                    root_res.find(".//Header/timestamp").text = ts_node.text

                # 3. orderInfo (workOrderId & serviceOrderId)
                order_info_req = root_req.find(".//{*}orderInfo")
                order_info_res = root_res.find(".//orderInfo")
                if order_info_req is not None:
                    order_info_res.set("workOrderId", order_info_req.attrib.get("workOrderId", "BEKLIYOR"))
                    order_info_res.set("serviceOrderId", order_info_req.attrib.get("serviceOrderId", "BEKLIYOR"))

                # 4. cpeSubscriptionID
                # Önce öznitelik (attribute) olarak ara
                cpe_req = root_req.find(".//{*}cpeInfo")
                cpe_res = root_res.find(".//cpeInfo")
                if cpe_req is not None and "cpeSubscriptionID" in cpe_req.attrib:
                    cpe_res.set("cpeSubscriptionID", cpe_req.attrib["cpeSubscriptionID"])
                else:
                    # Öznitelik yoksa tag içindeki ID'yi (resource id) dene
                    alt_id = root_req.findtext(".//{*}id")
                    if alt_id: cpe_res.set("cpeSubscriptionID", alt_id)

                # --- KAYNAK 2 (LOG) İŞLEMLERİ ---
                actual_date = root_log.findtext(".//ns13:actualEndDate", "", ns2)
                if actual_date: order_info_res.set("actualCompletionDate", actual_date.replace(" ", "T"))

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

                # SONUÇ GÖSTERİMİ
                final_xml = ET.tostring(root_res, encoding='unicode')
                st.subheader("Sonuç XML")
                st.code(final_xml, language='xml')

        except Exception as e:
            st.error(f"Hata detayı: {e}")