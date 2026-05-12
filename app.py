import streamlit as st
import xml.etree.ElementTree as ET
import re

# --- SABİT MPWO ŞABLONU ---
MPWO_SABLON = """<WorkOrderResponse>
	<Header>
		<activityName>Installation</activityName>
		<msgName>ManagePartnerWorkOrderResponse</msgName>
		<msgType>RESPONSE</msgType>
		<senderURI>ATTIP</senderURI>
		<destinationURI>CW</destinationURI>
		<originatorURI>unknown</originatorURI>
		<replyToURI>unknown</replyToURI>
		<failureToURI>unknown</failureToURI>
		<activityStatus>SUCCESS</activityStatus>
		<security>unknown</security>
		<securityType>unknown</securityType>
		<priority>4</priority>
		<userid>IYS</userid>
		<timestamp>2021-05-20T15:29:39</timestamp>
		<comunicationPattern>SimpleResponse</comunicationPattern>
		<comunicationStyle>RPC</comunicationStyle>
		<service>ManagePartnerWorkOrder</service>
		<version>unknown</version>
		<correlationID>BEKLIYOR</correlationID>
		<businessID>BEKLIYOR</businessID>
		<conversationID>BEKLIYOR</conversationID>
		<requestID>BEKLIYOR</requestID>
		<messageID>BEKLIYOR</messageID>
	</Header>
	<Body>
		<workOrderResponse>
			<orderInfo workOrderId="BEKLIYOR" serviceOrderId="BEKLIYOR" actualCompletionDate="2021-12-14T16:50:09" notes="-" resultCode="OK">
				<fieldSupportAvailability/>
				<fieldSupportUnavailabilityReason/>
			</orderInfo>
			<cpeInfo cpeSubscriptionID="BEKLIYOR" cpeEquipmentTypeCode="01" cpeEquipmentTypeName="MODEM" cpeEquipmentModelCode="CISCO 888-K9" cpeEquipmentModelName="CISCO 888-K9" cpeVendorCode="04" cpeVendorName="Cisco" cpeSerialNumber="141220211650" cpeMacAddress="" isCpeEquipmentReturned="" managementType="" managementIp="" isCpeChanged=""/>
		</workOrderResponse>
	</Body>
</WorkOrderResponse>"""

def get_cvalue(root, key_name, ns):
    """Log içindeki ns13:cValue etiketlerini bulur."""
    node = root.find(f".//ns13:cValue[@key='{key_name}']", ns)
    return node.text if node is not None and node.text is not None else ""

# --- Arayüz Ayarları ---
st.set_page_config(page_title="XML ID & Attribute Sync Tool", layout="wide")
st.title("XML ID & Attribute Sync Tool")

secim = st.selectbox("Mesaj Türü Seçin", ["MPWO", "Asup_Termination", "DSL_Termination"])

col1, col2 = st.columns(2)
with col1:
    raw1 = st.text_area("Kaynak XML 1 (Request Mesajı)", height=300)
with col2:
    raw2 = st.text_area("Kaynak XML 2 (Log/Exception Mesajı)", height=300)

st.write("---")

# İşlem Butonu
if st.button("Verileri Senkronize Et ve Oluştur", type="primary", use_container_width=True):
    raw1 = raw1.strip()
    raw2 = raw2.strip()

    if not raw1 or not raw2:
        st.warning("Lütfen her iki kutuya da veri yapıştırın.")
    else:
        try:
            # Namespaceler
            ns1 = {
                'esbCommonType': 'http://www.turktelekom.com.tr/aTTIP/Common/CommonType/1.0',
                'workOrderRequest': 'http://www.turktelekom.com.tr/aTTIP/Services/OrderFulfillment/ManagePartnerWorkOrder/WorkOrderRequest/1.0'
            }
            ns2 = {'ns13': 'http://www.innova.com.tr/WFM'}

            root_req = ET.fromstring(raw1)
            root_sablon = ET.fromstring(MPWO_SABLON)

            # Kaynak 2 (Log) içinden XML'i Regex ile ayıkla
            xml_match = re.search(r'<ns13:genericIYSMessageRequest.*</ns13:genericIYSMessageRequest>', raw2, re.DOTALL)
            if not xml_match:
                st.error("Kaynak 2'de geçerli bir XML log bloğu bulunamadı!")
            else:
                root_log = ET.fromstring(xml_match.group(0))

                if secim == "MPWO":
                    order_info_sablon = root_sablon.find(".//orderInfo")
                    cpe_info_sablon = root_sablon.find(".//cpeInfo")

                    # --- 1. KAYNAK 1 (REQUEST) İŞLEMLERİ ---
                    # Header Text Tagleri (Wildcard ile kesin bulma)
                    id_list = ["correlationID", "businessID", "conversationID", "requestID", "messageID"]
                    for id_name in id_list:
                        val_node = root_req.find(f".//{{*}}{id_name}")
                        if val_node is not None:
                            target_node = root_sablon.find(f".//{id_name}")
                            if target_node is not None:
                                target_node.text = val_node.text
                    
                    # Timestamp Update
                    ts_node = root_req.find(".//{*}timestamp")
                    if ts_node is not None:
                        root_sablon.find(".//timestamp").text = ts_node.text

                    # orderInfo Attributes (ID'ler)
                    req_order_info = root_req.find(".//{*}orderInfo")
                    if req_order_info is not None and order_info_sablon is not None:
                        order_info_sablon.set("workOrderId", req_order_info.attrib.get("workOrderId", "BEKLIYOR"))
                        order_info_sablon.set("serviceOrderId", req_order_info.attrib.get("serviceOrderId", "BEKLIYOR"))

                    # cpeSubscriptionID
                    found_sub_id = None
                    cpe_req_attr = root_req.find(".//{*}cpeInfo")
                    if cpe_req_attr is not None and "cpeSubscriptionID" in cpe_req_attr.attrib:
                        found_sub_id = cpe_req_attr.attrib["cpeSubscriptionID"]
                    if not found_sub_id:
                        found_sub_id = root_req.findtext(".//{*}subscriptionId")
                    if not found_sub_id:
                        found_sub_id = root_req.findtext(".//{*}id")
                    
                    if found_sub_id and cpe_info_sablon is not None:
                        cpe_info_sablon.set("cpeSubscriptionID", found_sub_id)

                    # --- 2. KAYNAK 2 (LOG) İŞLEMLERİ ---
                    # actualCompletionDate
                    actual_date = root_log.findtext(".//ns13:actualEndDate", "", ns2)
                    if actual_date and order_info_sablon is not None:
                        order_info_sablon.set("actualCompletionDate", actual_date.replace(" ", "T"))

                    # cpeInfo Attributes (Cihaz Özellikleri cValue'dan)
                    log_resource = root_log.find(".//ns13:resource", ns2)
                    if log_resource is not None and cpe_info_sablon is not None:
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
                            if val:
                                cpe_info_sablon.set(sab_attr, val)

                    # Sonuç oluştur ve ekrana bas
                    final_xml = ET.tostring(root_sablon, encoding='unicode')
                    st.success("Sonuç XML Başarıyla Oluşturuldu! (Sağ üstteki butondan kopyalayabilirsiniz)")
                    st.code(final_xml, language="xml")

        except Exception as e:
            st.error(f"İşlem sırasında hata:\n{e}")