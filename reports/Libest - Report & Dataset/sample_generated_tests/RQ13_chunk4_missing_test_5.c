/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk4_missing_test_5.c
 */

static void rq13_chunk4_missing_test_5 (void)
{
    long rv;

    LOG_FUNC_NM
    ;

    /*
     * 1) Valid enroll over HTTPS with proper CA certs and HTTP Basic creds
     *    should succeed (HTTP 200). This demonstrates normal HTTP-on-TLS flow.
     */
    rv = curl_http_post(US903_ENROLL_URL_BA, US903_PKCS10_CT,
                        US903_PKCS10_RSA2048,
                        US903_UIDPWD_GOOD, US903_CACERTS, CURLAUTH_BASIC,
                        NULL, NULL, NULL);
    CU_ASSERT(rv == 200);

    /*
     * 2) Omit CA certs: TLS verification should fail / handshake not trusted,
     *    resulting in a non-200 return from the libcurl helper. This asserts
     *    that the HTTP message is protected by TLS verification.
     */
    rv = curl_http_post(US903_ENROLL_URL_BA, US903_PKCS10_CT,
                        US903_PKCS10_RSA2048,
                        US903_UIDPWD_GOOD, /* cacerts */ NULL, CURLAUTH_BASIC,
                        NULL, NULL, NULL);
    CU_ASSERT(rv != 200);

    /*
     * 3) Provide CA certs but omit HTTP Basic credentials: TLS should still
     *    establish but the HTTP layer should reject with 401, demonstrating
     *    separation of TLS transport and HTTP authentication semantics.
     */
    rv = curl_http_post(US903_ENROLL_URL_BA, US903_PKCS10_CT,
                        US903_PKCS10_RSA2048,
                        /* uidpwd */ NULL, US903_CACERTS, CURLAUTH_BASIC,
                        NULL, NULL, NULL);
    CU_ASSERT(rv == 401);
}
