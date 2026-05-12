import streamlit as st
import xml.etree.ElementTree as ET

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

# --- Arayüz Ayarları ---
st.set_page_config(page_title="XML ID & Attribute Sync Tool", layout="wide")
st.title("XML ID & Attribute Sync Tool")

# Seçim Menüsü
secim = st.selectbox("Mesaj Türü Seçin", ["MPWO", "Asup_Termination", "DSL_Termination"])

# Kutular
col1, col2 = st.columns(2)
with col1:
    data1 = st.text_area("Kaynak XML 1 (Request Mesajı)", height=300)
with col2:
    txt_src2 = st.text_area("Kaynak XML 2 (Opsiyonel)", height=300)

st.write("---")

# İşlem Butonu
if st.button("Verileri Senkronize Et ve Oluştur", type="primary", use_container_width=True):
    data1 = data1.strip()

    if not data1:
        st.warning("Lütfen Kaynak 1 kutusuna Request XML'ini yapıştırın.")
    else:
        try:
            # Namespace tanımları
            ns = {
                'esbCommonType': 'http://www.turktelekom.com.tr/aTTIP/Common/CommonType/1.0',
                'workOrderRequest': 'http://www.turktelekom.com.tr/aTTIP/Services/OrderFulfillment/ManagePartnerWorkOrder/WorkOrderRequest/1.0'
            }

            root_request = ET.fromstring(data1)

            if secim == "MPWO":
                root_sablon = ET.fromstring(MPWO_SABLON)

                # 1. TEXT TAGLERİNİ GÜNCELLE (Header kısmındakiler)
                id_list = ["correlationID", "businessID", "conversationID", "requestID", "messageID"]
                for id_name in id_list:
                    val_node = root_request.find(f".//esbCommonType:{id_name}", ns)
                    if val_node is not None:
                        target_node = root_sablon.find(f".//{id_name}")
                        if target_node is not None:
                            target_node.text = val_node.text

                # 2. ATTRIBUTE (ÖZNİTELİK) GÜNCELLEME (orderInfo ve cpeInfo)
                
                # --- orderInfo Güncelleme ---
                req_order_info = root_request.find(".//workOrderRequest:orderInfo", ns)
                sablon_order_info = root_sablon.find(".//orderInfo")
                
                if req_order_info is not None and sablon_order_info is not None:
                    # workOrderId ve serviceOrderId kopyala
                    if "workOrderId" in req_order_info.attrib:
                        sablon_order_info.set("workOrderId", req_order_info.attrib["workOrderId"])
                    if "serviceOrderId" in req_order_info.attrib:
                        sablon_order_info.set("serviceOrderId", req_order_info.attrib["serviceOrderId"])

                # --- cpeInfo Güncelleme ---
                req_cpe_info = root_request.find(".//workOrderRequest:cpeInfo", ns)
                sablon_cpe_info = root_sablon.find(".//cpeInfo")

                if req_cpe_info is not None and sablon_cpe_info is not None:
                    if "cpeSubscriptionID" in req_cpe_info.attrib:
                        sablon_cpe_info.set("cpeSubscriptionID", req_cpe_info.attrib["cpeSubscriptionID"])

                # Sonuç
                final_xml = ET.tostring(root_sablon, encoding='unicode')
                
                st.success("Sonuç XML Başarıyla Oluşturuldu!")
                # Streamlit'te st.code bloğu sağ üstte otomatik kopyalama butonu ile gelir
                st.code(final_xml, language="xml")

        except Exception as e:
            st.error(f"İşlem sırasında hata:\n{e}")