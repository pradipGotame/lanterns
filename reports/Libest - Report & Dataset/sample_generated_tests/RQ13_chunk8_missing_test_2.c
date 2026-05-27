/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk8_missing_test_2.c
 */

static void rq13_chunk8_missing_test_2 (void)
{
    int rv;

    LOG_FUNC_NM
    ;

    /*
     * Start server with PoP enabled so the client is expected to include
     * the challengePassword (PoP) in the CSR.  We use the us1005 helper
     * which drives an EST client that will include the PoP when requested
     */
    st_stop();
    us1005_start_server(0, 0, 0, 1);

    /*
     * Ensure CSR attributes include the challengePassword OID (default)
     */
    st_set_csrattrs(NULL);

    /*
     * Look for client including the challengePassword in the CSR
     * (indicates the client generated the PoP attribute)
     */
    log_search_target = "Client will include challengePassword in CSR\0";
    search_target_found = 0;

    us1005_easy_provision("RQ13-TC-valid-pop", US1005_SERVER_IP, 0, 0);

    /*
     * Assert that the client did include the PoP in the CSR (log evidence).
     * This provides direct evidence the CSR contained a challengePassword.
     */
    CU_ASSERT(search_target_found == 1);

    /*
     * Now exercise the rejection path: enable PoP on the server but send
     * a request that does NOT include PoP (curl does not include PoP)
     * The server should reject the enroll with an HTTP failure code.
     */
    st_enable_pop();

    /*
     * Remove PoP from CSR attributes to simulate a CSR without PoP
     */
    st_set_csrattrs(US1005_CSR_NOPOP);

    rv = curl_http_post(US1005_ENROLL_URL_BA, US1005_PKCS10_CT,
                        US1005_PKCS10_RSA2048,
                        US1005_UIDPWD_GOOD, US1005_CACERTS, CURLAUTH_BASIC,
                        NULL, NULL, NULL);

    /*
     * The server should respond with a failure code when PoP is required
     */
    CU_ASSERT(rv == 400);

    /*
     * Cleanup - restore CSR attrs and stop server
     */
    st_set_csrattrs(NULL);
    st_disable_pop();
    st_stop();
}
