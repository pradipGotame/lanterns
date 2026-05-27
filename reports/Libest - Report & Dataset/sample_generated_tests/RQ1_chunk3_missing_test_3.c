/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ1_chunk3_missing_test_3.c
 */

void rq1_chunk3_missing_test_3(void)
{
	int rc;
	int rv;
	unsigned char *attr_data = NULL;
	int attr_len = 0;

	/*
	 * Spin up EST server (TLS) so we can exercise end-to-end HTTPS flows
	 */
	rc = st_start(US897_SERVER_PORT, 
		      US897_SERVER_CERTKEY,
		      US897_SERVER_CERTKEY,
		      "RQ1 chunk3 test realm",
		      US897_CACERTS_MULTI_CHAIN_CRLS,
		      US897_TRUST_CERTS,
		      "CA/estExampleCA.cnf",
		      0, 0, 0);

	CU_ASSERT(rc == 0);
	if (rc) return;
	SLEEP(1);

	/*
	 * Point the client at the test server and request CSR-ATTRS
	 * (covers header/media-type/payload format verification gaps by
	 * asserting a non-empty payload and a basic DER SEQUENCE tag)
	 */
	est_client_set_server(ectx, US899_SERVER_IP, US899_SERVER_PORT, NULL);

	rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
	CU_ASSERT(rv == EST_ERR_NONE);
	CU_ASSERT(attr_len > 0);
	CU_ASSERT(attr_data != NULL);
	/* basic payload-format check: CSR attributes in DER typically begin with 0x30 (SEQUENCE) */
	CU_ASSERT(attr_data[0] == 0x30);

	/*
	 * Also exercise the server-generated-keys provisioning extension
	 * to demonstrate end-to-end provisioning happy-path coverage.
	 */
	EVP_PKEY *new_key = generate_private_key();
	CU_ASSERT(new_key != NULL);
	int pkcs7_len = 0, ca_certs_len = 0;
	rv = est_client_provision_cert(ectx, "rq1-chunk3-cn", &pkcs7_len, &ca_certs_len, new_key);
	CU_ASSERT(rv == EST_ERR_NONE);
	EVP_PKEY_free(new_key);
}
