/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk9_missing_test_1.c
 */

static void rq13_chunk9_missing_test_1 (void)
{
    long rv;
    const char *bad_cmc_msg = "MALFORMED-CMC-TRANSPORT-PAYLOAD";

    LOG_FUNC_NM
    ;

    /*
     * Attempt to send a malformed CMC-style payload to the enroll URL
     * and assert the server rejects it (negative/error handling test).
     */
    st_enable_pop();

    rv = curl_http_post(US748_ENROLL_URL_BA,
                        US748_PKCS10_CT,
                        bad_cmc_msg,
                        US748_UIDPWD_GOOD,
                        US748_CACERTS,
                        CURLAUTH_BASIC,
                        NULL, NULL, NULL);

    /* Server should respond with a failure code for malformed transport */
    CU_ASSERT(rv == 400);

    st_disable_pop();
}
