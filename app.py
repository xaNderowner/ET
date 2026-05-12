import streamlit as st
import xml.etree.ElementTree as ET
import re

st.set_page_config(page_title="XML Sync Tool", layout="wide")

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

st.title("🚀 XML Sync Tool")

col1, col2 = st.columns(2)
with col1:
    raw1 = st.text_area("Kaynak 1 (Request XML)", height=300)
with col2:
    raw2 = st.text_area("Kaynak 2 (Log XML)", height=300)

if st.button("🔄 XML'i Oluştur", use_container_width=True):
    if raw1 and raw2:
        try:
            ns2 = {'ns13': 'http://www.innova.com.tr/WFM'}
            root_req = ET.fromstring(raw1)
            
            xml_match = re.search(r'<ns13:genericIYSMessageRequest.*</ns13:genericIYSMessageRequest>', raw2, re.DOTALL)
            if not xml_match:
                st.error("Log içerisinde XML bloğu bulunamadı!")
            else:
                root_log = ET.fromstring(xml_match.group(0))
                root_res = ET.fromstring(MPWO_SABLON)

                order_info_res = root_res.find(".//orderInfo")
                cpe_info_res = root_res.find(".//cpeInfo")

                id_list = ["correlationID", "businessID", "conversationID", "requestID", "messageID"]
                for id_name in id_list:
                    val_node = root_req.find(f".//{{*}}{id_name}")
                    if val_node is not None:
                        target = root_res.find(f".//Header/{id_name}")
                        if target is not None: target.text = val_node.text

                ts_node = root_req.find(".//{{*}}timestamp")
                if ts_node is not None:
                    root_res.find(".//Header/timestamp").text = ts_node.text

                order_info_req = root_req.find(".//{{*}}orderInfo")
                if order_info_req is not None and order_info_res is not None:
                    order_info_res.set("workOrderId", order_info_req.attrib.get("workOrderId", "BEKLIYOR"))
                    order_info_res.set("serviceOrderId", order_info_req.attrib.get("serviceOrderId", "BEKLIYOR"))

                found_sub_id = None
                cpe_req_node = root_req.find(".//{{*}}cpeInfo")
                if cpe_req_node is not None and "cpeSubscriptionID" in cpe_req_node.attrib:
                    found_sub_id = cpe_req_node.attrib["cpeSubscriptionID"]
                
                if not found_sub_id:
                    found_sub_id = root_req.findtext(".//{{*}}subscriptionId")
                
                if not found_sub_id:
                    found_sub_id = root_req.findtext(".//{{*}}id")

                if found_sub_id and cpe_info_res is not None:
                    cpe_info_res.set("cpeSubscriptionID", found_sub_id)

                actual_date = root_log.findtext(".//ns13:actualEndDate", "", ns2)
                if actual_date and order_info_res is not None:
                    order_info_res.set("actualCompletionDate", actual_date.replace(" ", "T"))

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

                final_xml = ET.tostring(root_res, encoding='unicode')
                st.code(final_xml, language='xml')
                st.success("İşlem başarıyla tamamlandı.")

        except Exception as e:
            st.error(f"Hata: {e}")